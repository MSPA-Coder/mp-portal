# MP Portal

Aplicação Django que recebe as solicitações de contato do site institucional da
MP Soluções e dá a elas um lugar para existir: um banco PostgreSQL, uma área de
atendimento com autenticação e um aviso de privacidade que descreve exatamente
o que é guardado.

É o repositório previsto pela **fase F7** do `LEVANTAMENTO_2026-09.md`
(repositório `manutencao`): Django, consumindo `sharedauth`, no padrão da frota
— Compose, CI, `/health`, `deploy.sh`, backup e vigia.

## O que existe hoje

| | |
|---|---|
| `POST /contato` | Recebe o formulário do site. Aceita formulário comum e JSON, valida, guarda e devolve um protocolo. |
| `GET /privacidade` | O aviso de privacidade, montado a partir de `contatos/privacidade.py`. |
| `GET /atendimento/` | Lista das solicitações. Exige conta com `is_staff`. |
| `GET /health` | Sonda que consulta o banco. Contrato comum aos aplicativos da frota. |

## O que ainda não existe, e não por esquecimento

- **Área do cliente.** O portal ainda não tem módulo com dado por cliente, e
  por isso não tem tabela de cliente: estrutura sem consumidor é especulação.
  A forma recomendada e o gatilho estão em
  [`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`](docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md).
- **Aviso de chegada.** Quando uma solicitação entra, nada avisa ninguém — ela
  fica na lista até alguém abrir. O motivo e o caminho estão em
  [`docs/operacao.md`](docs/operacao.md).
- **Publicação no VPS.** O portal não está no ar. O que falta, na ordem, está
  em [`docs/operacao.md`](docs/operacao.md).

## Rodar localmente

Pré-requisito: Docker. Os segredos são arquivos, não variáveis:

```bash
mkdir -p .secrets .certs
printf '%s' 'chave-local-de-desenvolvimento' > .secrets/django_secret_key
printf '%s' 'senha-local-postgres' > .secrets/postgres_password
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 30 \
  -keyout /tmp/ca.key -out .certs/local-root-ca.crt -subj "/CN=MpPortal Local CA"
```

Subir a aplicação como ela é servida (gunicorn, imagem imutável):

```bash
docker compose up --build
```

O portal responde em <http://127.0.0.1:5601>. A primeira conta:

```bash
docker compose run --rm web python manage.py createsuperuser
```

Desenvolvimento com recarga automática:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

## Rodar a suíte

```bash
docker compose --profile quality run --build --rm quality
```

O `--build` **não é opcional**: o serviço `quality` não monta o código do host,
e `docker compose run` sem ele reaproveita a imagem anterior — a suíte passaria
em verde sobre o código de antes.

A suíte inteira toca o banco. Isso é resposta ao achado L01 do levantamento: as
restrições (`CheckConstraint`), as migrações e a autorização são exercitadas
contra um PostgreSQL de verdade — efêmero, em tmpfs, e deliberadamente separado
do banco com dados.

## Configuração

Copie `.env.docker.example` para `.env.docker` e ajuste. Dois pontos merecem
atenção:

- **`CONTATO_ORIGENS_PERMITIDAS` vazio recusa todo envio** fora do modo de
  depuração. É proposital: esquecer de configurar vira um 403 visível, e não um
  endpoint aberto.
- **Com `USE_HTTPS=True`, a aplicação recusa subir** sem
  `CSRF_TRUSTED_ORIGINS`, `CONTATO_CANAL_TITULAR` e
  `CONTATO_ORIGENS_PERMITIDAS`. Uma implantação pública sem canal para o
  titular publica um aviso de privacidade que não tem como ser cumprido.

## Retenção

```bash
docker compose run --rm web python manage.py expurgar_contatos --simular
docker compose run --rm web python manage.py expurgar_contatos
```

Apaga o que passou de `CONTATO_RETENCAO_DIAS` (730 por padrão), preservando o
que foi marcado como convertido em cliente. Ainda **não** roda sozinho: o timer
entra junto com a publicação.

## Documentação

- [`AGENTS.md`](AGENTS.md) — invariantes e como trabalhar neste repositório.
- [`docs/operacao.md`](docs/operacao.md) — o que falta para publicar, e o que a
  publicação aciona.
- [`docs/adr/`](docs/adr) — as duas decisões que custam caro para reverter.
