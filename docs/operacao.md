# Operação

O portal está em produção em `mp-solucoes.duckdns.org`. Entrou no ar em
10/09/2026, no lugar do site estático, e desde 13/09/2026 roda num **VPS
dedicado** (Ubuntu 26.04, ARM64), separado do servidor que atende os outros
aplicativos. O domínio não mudou; a troca foi feita no DuckDNS.

A infraestrutura é a do repositório `manutencao`, igual à do outro VPS:
`deploy.sh`, backup diário do banco, vigia, sentinela de 5xx, autocura, alerta
e nginx. Nenhum script guarda lista de aplicações — cada um descobre o que
existe na máquina em que roda —, então o mesmo código serve um servidor com
quatro aplicativos e outro só com o portal.

## Como roda

- Checkout em `~/apps/mp-portal`, espelho de `main`, com deploy key própria
  somente leitura.
- Atualização: `~/deploy.sh portal --check` e `~/deploy.sh portal`
  (fast-forward, rebuild, `/health` público e rollback automático de código e
  imagem — migração não é revertida). `~/deploy.sh --status` mostra o SHA do
  servidor ao lado do GitHub.
- Configuração em `.env.vps` (modelo em `.env.vps.example`), que é o nome que o
  `deploy.sh` lê; o `.env.docker.example` continua servindo de guia.
- Segredos: `.secrets/postgres_password` e `.secrets/postgres_app_password`
  legíveis pelo uid 70 do PostgreSQL (`chmod 444`). O primeiro é do papel
  administrativo (`POSTGRES_USER`, superusuário, dono das tabelas), que só o
  banco, o `db-provision` e o `migrate` recebem; o segundo é do papel restrito
  `mp_portal_app` (só DML), com que o `web` conecta — e a aplicação recusa
  conexão superusuária (`core/papel_do_banco.py`). `.secrets/django_secret_key` do uid 999 (`app` da imagem), em
  modo `400`. Segredo `0600` do usuário `ubuntu` faz o contêiner morrer no
  arranque. `.certs/local-root-ca.crt` existe, vazio.
- `ALLOWED_HOSTS` inclui `localhost,127.0.0.1` além do domínio: o healthcheck
  do Compose chama `127.0.0.1:8000/health`, e sem isso o Django responde 400.
- `CONTATO_PROXIES_CONFIAVEIS=172.16.0.0/12` cobre o gateway da rede do
  Compose, que é o `REMOTE_ADDR` que o contêiner vê.
- Backup: dump diário de `mp_portal` em `~/backups/mp_portal/`, relido com
  `pg_restore --list` e com SHA-256. O BackupRestore, no host do mantenedor,
  busca esses dumps todo dia (projeto `mp_portal_vps`, servidor `portal`),
  confere o SHA-256, cataloga e ensaia a restauração fora do servidor.
- Retenção: o `expurgo-contatos.timer` do repositório `manutencao` roda
  `manage.py expurgar_contatos` uma vez por dia no contêiner `web`, e falha
  alto se o portal estiver no servidor sem contêiner para rodá-lo.
- Aviso de chegada: o `aviso-contatos.timer` do mesmo repositório roda
  `manage.py contatos_novos` a cada 15 minutos e chama o `alerta.sh` quando há
  solicitação nova. A mensagem leva só a contagem — nenhum dado pessoal vai
  para o Telegram —, e quem recebe abre `/painel/atendimento/`. O canal é o
  mesmo dos outros alertas do servidor.
- GitHub: repositório privado, com alertas e correções de segurança do
  Dependabot ligados.

## O que ficou aberto

### Alto — riscos aceitos que a publicação disparou

- **L06 — RTO nunca medido.** O gatilho era o portal entrar no ar. Falta medir
  quanto tempo o ambiente leva para voltar do zero e conferir o
  `KIT_RECUPERACAO.md` do BackupRestore. O site institucional cai junto com a
  aplicação.
- **L19 — DuckDNS.** Sufixo compartilhado, sem autoridade de domínio e sem
  e-mail no domínio. Trocar de domínio é um passo próprio, e destrava o e-mail
  — inclusive o canal do titular abaixo.

### Médio — `main` sem proteção de branch (L11)

Plano gratuito não oferece ruleset, status check obrigatório nem CodeQL em
repositório privado. Um defeito nesta `main` derruba o site e toca dado de
terceiro. Reavaliar junto com o domínio ou o plano.

### Médio — e-mail comercial ainda mascarado (L16)

O e-mail comercial continua com asteriscos em `templates/site/_rodape.html`:
publicar contato falso é pior que não publicar.

### Médio — canal do titular é placeholder

`CONTATO_CANAL_TITULAR` aponta para um endereço no DuckDNS, que não recebe
e-mail. A aplicação exige a variável e o aviso de privacidade a publica. Um
alias encaminhado no domínio próprio resolve sem custo — depende de L19.
