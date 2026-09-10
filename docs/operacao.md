# Operação: a virada (feita em 10/09/2026) e o que ficou aberto

O portal **está publicado**. Desde 10/09/2026, quem atende
`mp-solucoes.duckdns.org` é esta aplicação Django (contêiner `mp-portal-web-1`,
porta 5601), no lugar do site estático (porta 5501) que servia antes. A virada
foi uma **substituição de serviço no ar**: mesmo domínio, mesmo certificado, o
`proxy_pass` do vhost apontando para a porta nova.

O repositório de origem do site antigo (`mp-solucoes`, no GitHub, e a pasta
local `MpSolucoes`) foi removido em 10/09/2026; a F5 está no bundle
`mp-solucoes-f5-arquivo.bundle` (em `Dropbox/Programacao/`).

Este documento deixou de ser uma lista de preparação e passou a registrar **o
que foi feito** e **o que ficou aberto**.

## O que a virada executou

| Passo | Estado |
|---|---|
| Clone de `mp-portal` em `~/apps/mp-portal` no VPS, com chave de deploy própria (`deploy_portal`) | ✅ |
| `.env.vps` + `.secrets/{django_secret_key,postgres_password}` + `.certs/local-root-ca.crt` | ✅ |
| `docker compose up -d --build`: imagem construída, migrações aplicadas, `postgres`+`web` `healthy` | ✅ |
| `manutencao` PR #25: `deploy.sh` verbo `portal`, vhost `portal` no lugar de `mp-solucoes`, `mp_portal` no `backup-db.sh` | ✅ mesclado |
| `vps/instalar.sh` e `instalar-nginx.sh` no servidor | ✅ |
| Troca do symlink `sites-enabled`: `portal` entra, `mp-solucoes` sai, `nginx -t` + reload | ✅ |
| Verificação pública (ver §"Verificação" abaixo) | ✅ |
| `mp-solucoes-web-1` parado e removido; `~/apps/mp-solucoes` e o vhost órfão apagados; imagem podada | ✅ |
| Primeiro backup de `mp_portal`, relido com `pg_restore --list` | ✅ |
| Superusuário `Mariano` no banco de produção | ✅ |

Detalhes que divergiram do previsto, para quem repetir o padrão noutro app:

- **O env do servidor é `.env.vps`**, não `.env.docker` — é o nome que o
  `deploy.sh` da frota lê. O `.env.docker.example` continua valendo como guia;
  o arquivo servido chama-se `.env.vps` (há um `.env.vps.example` no repo).
- **Permissão dos segredos**: `postgres_password` precisa ser legível pelo uid
  70 (`chmod 444`); `django_secret_key` pertence ao uid 999 (`app` da imagem)
  em modo `400`. Segredo `0600 ubuntu:ubuntu` faz o contêiner morrer no
  arranque.
- **`ALLOWED_HOSTS` precisa de `localhost,127.0.0.1`** além do domínio: o
  healthcheck do Compose bate em `127.0.0.1:8000/health`, e sem isso o Django
  responde 400 e o contêiner nunca fica `healthy`.
- **`CONTATO_PROXIES_CONFIAVEIS=172.16.0.0/12`** cobre o gateway da rede do
  Compose (`172.23.0.1` hoje), que é o que o contêiner vê como `REMOTE_ADDR`.

## Verificação feita na virada

- as sete páginas institucionais em 200, `/contato` e `/privacidade` em 200, os
  `.html` antigos em 301;
- `POST /contato` com token CSRF → 303 para `/contato/recebido`, registro no
  banco (`Contato`), e o de teste apagado depois;
- `POST /contato` sem token CSRF → 403;
- `/atendimento/` e `/tarefas/` sem sessão → 302 para `/login`;
- `robots.txt` e `sitemap.xml` com `mp-solucoes.duckdns.org` **derivado do
  request**, sem o domínio escrito em arquivo — a propriedade da F5 sobreviveu;
- `http://` → 301 `https://`; HSTS presente;
- `/health` → `{"servico": "mp-portal", "status": "ok"}` no `vigia.sh --estado`
  e no `deploy.sh --status`;
- backup de `mp_portal` no ciclo diário, relido com `pg_restore --list`.

## O que ficou aberto

### Alto — a retenção do aviso de privacidade é promessa

**O timer do expurgo não existe.** `manage.py expurgar_contatos` aplica o prazo
que o aviso de privacidade publica (`CONTATO_RETENCAO_DIAS`, 730), e hoje
ninguém o executa. Enquanto não houver timer no host — diário, no formato dos
outros da frota (`manutencao/vps/`) — o prazo declarado é letra morta. É o
primeiro item.

### Alto — riscos aceitos que a virada disparou (LEVANTAMENTO §6)

- **L06 — RTO nunca medido.** O gatilho era literal: *"antes de o portal do
  cliente entrar no ar"*. O portal entrou. Falta medir quanto tempo o ambiente
  inteiro leva para voltar do zero, e conferir o `KIT_RECUPERACAO.md`. Agora
  pesa mais: o site institucional cai junto com a aplicação.
- **L19 — DuckDNS.** Sufixo compartilhado, sem autoridade de domínio, sem
  e-mail no domínio. A virada foi feita **mantendo** `mp-solucoes.duckdns.org`
  por decisão do mantenedor; a troca de domínio é um passo próprio, e destrava
  o e-mail (inclusive o canal do titular abaixo).

### Alto — o achado L11 mudou de repositório

`main` do `mp-portal` sem branch protection. O achado L11 valia para o
`mp-solucoes` (removido) e migrou para cá **disparado**: o defeito nesta `main`
derruba o site institucional **e** vaza dado pessoal de terceiro. Plano
gratuito não tem ruleset em repo privado — reavaliar com o domínio/plano.

### Médio — dados de contato ainda mascarados (L16)

Telefone, WhatsApp e e-mail comercial continuam com asteriscos em
`templates/site/_rodape.html` e `templates/site/contato.html`. Publicar contato
falso é pior que não publicar — então o site está no ar sem eles.

### Médio — canal do titular é placeholder

`CONTATO_CANAL_TITULAR=privacidade@mp-solucoes.duckdns.org` no `.env.vps`. É um
endereço **não funcional** (DuckDNS não faz e-mail); a aplicação exige a
variável preenchida, e o aviso de privacidade a publica. Um alias encaminhado
(`privacidade@`) no domínio próprio resolve sem custo — depende de L19.

### Médio — o aviso de chegada

Quando uma solicitação entra, nada avisa ninguém: fica na lista até alguém
abrir `/atendimento/`. A solução não é `EmailBackend` no contêiner (`read_only`,
sem token do Telegram, e não deveria ter). O caminho da frota é um script no
host, com timer, que consulta o portal e chama o `alerta.sh` quando houver
solicitação nova.

## O que **não** é mais necessário

Tarefas que existiam enquanto o site e o portal eram dois, e a incorporação
eliminou — ficam registradas para que ninguém as procure:

- ligar o formulário do site ao endpoint do portal;
- renomear campos do formulário no outro repositório (que nem existe mais);
- afrouxar `form-action` / `connect-src` na CSP do site;
- configurar lista de origens, CORS e pré-voo;
- manter o verbo `mp` / vhost `mp-solucoes` / contêiner do site estático — tudo
  removido na virada.
