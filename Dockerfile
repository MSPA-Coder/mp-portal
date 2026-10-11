# syntax=docker/dockerfile:1.7
# Base fixada por DIGEST do indice multi-arquitetura, e nao pela tag: a tag
# `python:3.14-slim` e alvo movel, e a imagem que a CI varreu podia nascer de
# uma base diferente da que roda depois. E o mesmo digest dos irmaos da frota.
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
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip setuptools

# Versao fixa: o instalador que garante reprodutibilidade nao pode ser ele
# proprio uma variavel.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade "uv==0.12.10"

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# Duas fases. Primeiro so as dependencias, numa camada que so se invalida
# quando `uv.lock` muda.
#
# O FLAG E `--locked`, E A DIFERENCA IMPORTA. `--frozen` apenas usa o lock sem
# olhar o `pyproject.toml`: com o lock desatualizado ele sai com SUCESSO e
# instala as versoes antigas, em silencio. `--locked` REPROVA.
#
# `sharedauth` vem de repositorio Git, e o lock o prende ao COMMIT, nao a tag.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --extra dev

# `quality` e a unica imagem do projeto: roda Ruff e a suite, e tambem o
# gerador (`docker compose run --rm gerar`). Nada daqui vai para a hospedagem --
# o que vai e a pasta `dist/site` que o gerador produz.
FROM base AS quality

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --extra dev

ENV PYTHONPATH=/workspace \
    RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"

CMD ["sh", "-c", "ruff check . && ruff format --check . && pytest"]
