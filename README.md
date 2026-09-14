# MP Portal

O site e o sistema da **MP Soluções Corporativas**, numa aplicação só.

- **Sete páginas institucionais públicas** — início, soluções, método,
  segmentos, parceiros, empresa e contato. Ninguém precisa de conta para ler,
  navegar ou pedir um orçamento.
- **Um formulário de contato com destino real** — o pedido vai para o
  PostgreSQL, com consentimento registrado e prazo de retenção que é cumprido
  por comando.
- **Um painel com login** (`/painel/`) — as tarefas, que o mantenedor e mais
  três pessoas compartilham no lugar de mensagens de WhatsApp; o atendimento,
  onde a equipe da MP tria as solicitações; e as contas. Tem casca própria,
  separada do site (ver `docs/adr/0005-area-logada-com-casca-propria.md`). É a
  área que vai crescer.

Está em produção em `mp-solucoes.duckdns.org`, num VPS dedicado, com o mesmo
padrão operacional dos outros aplicativos: Django, `sharedauth`, Compose, CI,
`/health`, `deploy.sh`, backup e vigia.

## Rotas

| | |
|---|---|
| `/`, `/solucoes`, `/metodo`, `/segmentos`, `/parceiros`, `/empresa` | Páginas institucionais. Não consultam o banco. |
| `/contato` | A página com o formulário (GET) e o recebimento (POST), na mesma rota. |
| `/privacidade` | O aviso de privacidade, montado a partir de `contatos/privacidade.py`. |
| `/login` → `/apos-login` | Entrada. O destino sai da conta, não de um endereço fixo. `/login` fica na raiz porque o nginx central limita `POST /login`. |
| `/painel/tarefas/` | Tarefas, com responsável, prazo, situação e linha do tempo. Exige sessão (`login_required`). |
| `/painel/atendimento/` | Lista e ficha das solicitações, com responsável e reatribuição. Exige `is_staff`. |
| `/painel/contas/` | Cria e edita as contas do portal. Exige `is_staff`. |
| `/health` | Sonda que consulta o banco. Contrato comum aos aplicativos da frota. |
| `/robots.txt`, `/sitemap.xml` | Gerados da mesma tabela que monta o menu. |

## O que ainda não existe, e não por esquecimento

- **Área do cliente.** É destino declarado — a área autenticada terá dois
  públicos, clientes e equipe, em áreas separadas. Mas ainda não há serviço
  definido para pôr lá, e tabela sem consulta que a leia é especulação. A
  emenda por onde ela entra já existe (o destino derivado do login); a forma e
  o gatilho estão em
  [`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`](docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md).
- **Aviso de chegada.** Quando uma solicitação entra, nada avisa ninguém — ela
  fica na lista até alguém abrir. O motivo e o caminho estão em
  [`docs/operacao.md`](docs/operacao.md).
- **Dados de contato reais.** Telefone e e-mail continuam mascarados com
  asteriscos, por decisão registrada (achado L16): publicar contato falso é
  pior que não publicar.

## Rodar localmente

Pré-requisito: Docker. Os segredos são arquivos, não variáveis:

```bash
mkdir -p .secrets .certs
printf '%s' 'chave-local-de-desenvolvimento' > .secrets/django_secret_key
printf '%s' 'senha-local-postgres' > .secrets/postgres_password
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 30 \
  -keyout /tmp/ca.key -out .certs/local-root-ca.crt -subj "/CN=MpPortal Local CA"
```

Subir como é servido (gunicorn, imagem imutável):

```bash
docker compose up --build
```

Responde em <http://127.0.0.1:5601>. A primeira conta da equipe:

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

A suíte inteira toca o banco. É resposta ao achado L01 do levantamento: as
restrições (`CheckConstraint`), as migrações e a autorização são exercitadas
contra um PostgreSQL de verdade — efêmero, em tmpfs, e deliberadamente separado
do banco com dados.

## Configuração

Copie `.env.docker.example` para `.env.docker` e ajuste. O ponto que mais
importa: **com `USE_HTTPS=True` a aplicação recusa subir** sem
`CSRF_TRUSTED_ORIGINS` e sem `CONTATO_CANAL_TITULAR`. Uma implantação pública
sem canal para o titular publica um aviso de privacidade que não tem como ser
cumprido.

## Retenção

```bash
docker compose run --rm web python manage.py expurgar_contatos --simular
docker compose run --rm web python manage.py expurgar_contatos
```

Apaga o que passou de `CONTATO_RETENCAO_DIAS` (730 por padrão), preservando o
que foi marcado como convertido em cliente. Em produção, roda sozinho uma vez
por dia, pelo `expurgo-contatos.timer` do repositório `manutencao`.

## Documentação

- [`AGENTS.md`](AGENTS.md) — invariantes e como trabalhar neste repositório.
- [`docs/operacao.md`](docs/operacao.md) — como o portal roda em produção e o
  que ficou aberto.
- [`docs/adr/`](docs/adr) — as cinco decisões que custam caro para reverter: a
  incorporação do site (0003), a reversão que ela provocou (0001), o cliente
  adiado até existir módulo (0002), o módulo de tarefas ser daqui e não de fora
  (0004) e a casca própria do painel (0005).
