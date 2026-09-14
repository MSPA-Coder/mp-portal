# syntax=docker/dockerfile:1.7
# Base fixada por DIGEST do indice multi-arquitetura, e nao pela tag.
#
# `python:3.14-slim` e alvo movel: a tag e reapontada a cada republicacao, e
# como o `deploy.sh` reconstroi no VPS, a imagem servida podia nascer de uma
# base diferente da que a CI varreu. Mesmo raciocinio que ja fixa as actions por
# SHA e o Trivy por digest. Digest de INDICE, para valer em amd64 e arm64. E o
# mesmo digest dos irmaos da frota -- divergir sem motivo custaria uma segunda
# base para manter.
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN --mount=type=secret,id=local_ca,required=false \
    if [ -f /run/secrets/local_ca ]; then \
        cp /run/secrets/local_ca /usr/local/share/ca-certificates/local-root-ca.crt; \
        update-ca-certificates; \
    fi

# Correcoes de seguranca da base e das ferramentas de empacotamento.
#
# `apt-get upgrade` porque a `python:3.14-slim` publicada carrega pacotes do
# Debian com CVE ja corrigido a montante; sem isto a correcao so chega quando a
# imagem oficial for republicada.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip setuptools


# builder: resolve as dependencias a partir do `uv.lock`, num venv isolado.
#
# O FLAG E `--locked`, E A DIFERENCA IMPORTA. `--frozen` apenas usa o lock sem
# olhar o `pyproject.toml`: com o lock desatualizado ele sai com SUCESSO e
# instala as versoes antigas, em silencio. `--locked` confere e REPROVA quando
# alguem edita a declaracao e esquece de rodar `uv lock`.
#
# `sharedauth` vem de repositorio Git, e o lock o prende ao COMMIT, nao a tag.
# `git` fica so aqui: a imagem final copia o venv e nao herda o binario.
FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Versao fixa: o instalador que garante reprodutibilidade nao pode ser ele
# proprio uma variavel. O estagio `quality` copia este binario em vez de
# reinstala-lo.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade "uv==0.12.10"

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Duas fases. Primeiro so as dependencias, numa camada que so se invalida
# quando `uv.lock` muda -- editar template ou teste nao refaz a resolucao.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Agora o codigo e a instalacao do proprio projeto como wheel. `COPY . .` no
# lugar de listar cada app: a lista de pacotes vive num lugar so, o
# `[tool.hatch.build.targets.wheel]` do `pyproject.toml`, e o que NAO entra na
# imagem vive num lugar so, o `.dockerignore`. App novo esquecido no
# `pyproject` faz o build de wheel reprovar aqui -- nao vira 500 em producao.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable


# quality: Ruff e a suite, mais o servidor de desenvolvimento montado por
# compose.dev.yaml. Nunca e o estagio publicado: `compose.yaml` usa `runtime`
# para migrate e web.
FROM base AS quality

COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# O codigo inteiro vem antes da instalacao porque a suite exercita a aplicacao
# real, e nao so o pacote instalado.
COPY . .

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# `--extra dev` acrescenta as ferramentas de teste ao MESMO conjunto que o
# runtime instala: a suite tem de medir o que a imagem servida usa, e o lock
# garante que sejam as mesmas versoes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --extra dev

# `logs/` e estado local e fica fora do contexto de build. O estagio de
# qualidade ainda precisa do diretorio para configurar o handler Django.
RUN mkdir -p /workspace/logs

ENV DJANGO_SETTINGS_MODULE=portal.settings \
    PYTHONPATH=/workspace \
    RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"

# Sem o manifesto, renderizar qualquer template que use `{% static %}` estoura
# com "Missing staticfiles manifest entry" -- a suite ficaria sem conseguir
# exercitar a tela de login. As credenciais sao de build, nao de execucao.
RUN DJANGO_SECRET_KEY=build-only-nao-usada-em-execucao \
    POSTGRES_PASSWORD=build-only \
    python manage.py collectstatic --noinput --clear >/dev/null

EXPOSE 8000

CMD ["sh", "-c", "ruff check . && pytest"]


# Estagio de producao: somente dependencias e arquivos de runtime. Codigo fica
# como root:root e legivel pelo usuario da aplicacao; apenas volumes declarados
# pelo Compose sao gravaveis em execucao.
FROM base AS runtime

# O venv vem do `builder`; sem isto, `python`, `gunicorn` e `manage.py`
# resolveriam para o interpretador do sistema, que nao tem as dependencias.
ENV PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --home-dir /workspace app \
    && mkdir -p /workspace/staticfiles /workspace/logs \
    && chown app:app /workspace/staticfiles /workspace/logs

COPY --from=builder /opt/venv /opt/venv

# `COPY . .` no lugar de uma linha por app: o `.dockerignore` e a lista unica do
# que NAO entra na imagem, e nao ha uma segunda lista de apps para esquecer de
# atualizar. `BASE_DIR` se deriva de `portal/settings.py` estar em
# `/workspace/portal`, entao o codigo precisa estar aqui mesmo com o wheel
# instalado no venv.
COPY . .
RUN chmod 755 manage.py

# Tripwire de build: app faltando na arvore, erro de import ou de configuracao
# de app quebra aqui, e nao no primeiro request em producao. `check` carrega
# todos os apps e nao toca o banco. As credenciais sao de build.
#
# O `rm` no fim NAO e limpeza cosmetica. Este `check` roda como ROOT -- `USER
# app` so vem adiante --, e configurar o logging do Django abre o handler de
# arquivo, criando `/workspace/logs/portal.log` com dono root. Um volume
# nomeado novo e semeado com o conteudo do diretorio da imagem, entao esse
# arquivo root vai junto, e o contêiner, que roda como `app`, morre no arranque
# com "PermissionError: /workspace/logs/portal.log".
#
# Nao aparece em servidor que ja rodava antes deste tripwire: o Docker so
# semeia volume VAZIO, e o volume de la ja tinha um `portal.log` do dono certo.
# O defeito so se manifesta em instalacao nova -- descoberto ao montar o
# segundo VPS. Log de build nao tem o que fazer na imagem servida.
RUN DJANGO_SECRET_KEY=build-only-nao-usada-em-execucao \
    POSTGRES_PASSWORD=build-only \
    PYTHONPATH=/workspace \
    python manage.py check \
 && rm -f /workspace/logs/portal.log

# Tira `pip` e `setuptools` da imagem SERVIDA.
#
# Sao ferramenta de build e nao tem uso aqui -- o mesmo raciocinio que mantem
# `gcc`, `make` e `wget` fora do runtime, o que a CI verifica. A ultima linha e
# a propria verificacao: se `pip` continuar no PATH, o build falha aqui em vez
# de entregar uma imagem que so parece limpa.
RUN set -eu; \
    for raiz in /usr/local/lib/python*/site-packages /opt/venv/lib/python*/site-packages; do \
      [ -d "$raiz" ] || continue; \
      rm -rf "$raiz"/pip "$raiz"/pip-*.dist-info \
             "$raiz"/setuptools "$raiz"/setuptools-*.dist-info \
             "$raiz"/pkg_resources "$raiz"/_distutils_hack \
             "$raiz"/distutils-precedence.pth \
             "$raiz"/wheel "$raiz"/wheel-*.dist-info; \
    done; \
    rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.* \
          /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.*; \
    ! command -v pip

USER app

ENV DJANGO_SETTINGS_MODULE=portal.settings \
    PYTHONPATH=/workspace

EXPOSE 8000

# O health check e declarado no compose.yaml, nao aqui: ele depende do cabecalho
# X-Forwarded-Proto que o proxy reverso injeta, contexto que a imagem nao tem
# como conhecer. Os irmaos da frota seguem a mesma regra.

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "4", "--worker-class", "gthread", "--timeout", "60", "--no-control-socket", "portal.wsgi:application"]
