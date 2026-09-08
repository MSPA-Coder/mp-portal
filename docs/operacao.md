# Operação: o que falta para o portal existir no mundo

O portal **não está publicado**. Este documento é a lista do que falta, na
ordem em que precisa acontecer, e o que cada passo aciona. Ele existe para que
o dia da publicação seja uma execução, e não uma redescoberta.

## 0. Antes de qualquer coisa: três decisões voltam à mesa

A §6 do `LEVANTAMENTO_2026-09.md` registra cinco riscos aceitos, cada um com o
gatilho que deve fazer a decisão ser revisitada. **Publicar o portal dispara
três deles.**

| Achado | O que estava aceito | Por que dispara agora |
|---|---|---|
| **L06** — RTO nunca medido | Sabe-se que o dump restaura; não se sabe em quanto tempo o ambiente inteiro volta. | O gatilho escrito é literal: *"antes de o portal do cliente entrar no ar — a partir daí, a indisponibilidade tem custo para terceiro"*. Um formulário que não responde é um cliente que não chega. |
| **L19** — DuckDNS | Sufixo compartilhado, sem autoridade de domínio, sem e-mail corporativo. | O aviso de privacidade precisa publicar um canal para o titular. `algo@gmail.com` num aviso de privacidade de empresa é o tipo de detalhe que corrói confiança, e o domínio próprio resolve os dois de uma vez. |
| **L11** — `mp-solucoes` sem branch protection | `main` aceita force-push, sem status check obrigatório (recurso pago no plano atual). | O portal guarda dado pessoal de terceiro. O que se aceita para um site institucional não é o mesmo que se aceita para um repositório cujo defeito vaza dado de outra pessoa. |

Nenhum dos três é bloqueio técnico. Os três são decisões suas, e estão aqui
porque decisão adiada que não é reencontrada no momento certo vira risco
esquecido.

## 1. Infraestrutura no repositório `manutencao`

Editar `vps/` lá **não implanta nada** — a cópia do servidor é a que roda.
Depois de mudar: `bash vps/instalar.sh` no VPS e conferir com `--check`.

- **vhost novo** em `vps/nginx/`, apontando para `127.0.0.1:5601`, no mesmo
  formato dos cinco existentes. O limite de taxa de `POST /login` do
  `conf.d/00-comum.conf` já pega o portal de graça — a rota chama `/login`
  exatamente por isso.
- **`deploy.sh`**: verbo novo (`portal`), com o `/health` público na sonda.
- **`backup-db.sh`**: o banco `mp_portal` entra no ciclo diário. É o primeiro
  banco da frota com dado pessoal de terceiro — vale conferir a retenção dos
  dumps à luz disso.
- **`vigia.sh`**: mais um `/health` a vigiar.
- **`uptimerobot-monitores.sh`**: monitor externo do endpoint público.
- O **sentinela** e a **autocura** já cobrem o portal sem mudança: um lê o log
  de 5xx por host, o outro reinicia contêiner `unhealthy`.
- **timer do expurgo**: `manage.py expurgar_contatos` precisa rodar sozinho, ou
  o prazo declarado no aviso de privacidade é uma promessa que ninguém cumpre.
  Diário, no mesmo formato dos outros timers.

## 2. Segredos e variáveis no VPS

Dois arquivos em `.secrets/` (`django_secret_key`, `postgres_password`) e, no
`.env.docker`:

```
USE_HTTPS=True
ALLOWED_HOSTS=<host público>
CSRF_TRUSTED_ORIGINS=https://<host público>
CONTATO_ORIGENS_PERMITIDAS=https://<origem do site>
CONTATO_PROXIES_CONFIAVEIS=<rede do nginx central>
CONTATO_CANAL_TITULAR=<endereço para o titular>
```

Com `USE_HTTPS=True` e qualquer um dos três últimos ausente, **a aplicação
recusa subir** (`contatos/checks.py`). É deliberado: um aviso de privacidade que
promete um canal inexistente é pior do que não ter aviso.

## 3. Ligar o formulário do site

Hoje `contato.html` do `MpSolucoes` valida os campos e diz na tela que nada saiu
do navegador. São três ajustes pequenos lá:

1. **`action` e `method`** no `<form>`, apontando para a rota do portal.
2. **`name="solucoes"`** nas caixas de solução (hoje é `name="sol"`) e `value=`
   com os códigos do catálogo (`seguranca_eletronica`, `portaria`, `facilities`,
   `integradas`); o mesmo para o `<select>` de segmento (`condominios`,
   `industrias`, `empresas`, `comercio`, `saude`, `educacao`, `setor_publico`,
   `outro`). Os códigos são estáveis; o texto exibido pode mudar sem quebrar
   registro antigo.
3. **caixa de consentimento** obrigatória, com link para o aviso de privacidade,
   e remoção do aviso de rascunho e do `formOk` que simula envio.

### Onde a rota deve morar, e por quê

Duas formas, e a recomendação é a primeira:

- **Mesma origem, pelo nginx central** — o vhost do site passa `POST /contato`
  (e só ele) para o contêiner do portal. Não há CORS, não há pré-voo, e a CSP do
  site continua com `form-action 'self'`. Se o envio for por `fetch`, o único
  afrouxamento é `connect-src 'self'` no lugar de `'none'`.
- **Origem do portal, com CORS** — o formulário envia direto para
  `https://portal.<domínio>/contato`. Funciona (a rota já responde ao pré-voo e
  ecoa `Access-Control-Allow-Origin`), mas exige afrouxar `form-action` ou
  `connect-src` na CSP do site para incluir o host do portal.

A primeira mantém a CSP do site praticamente intacta, que foi trabalho da fase
F5 e não deve ser desfeito por conveniência.

## 4. O aviso de chegada

Quando uma solicitação entra, **nada avisa ninguém** — ela fica na lista até
alguém abrir. Isso é conhecido, não é esquecimento, e a solução não é um
`EmailBackend` dentro do contêiner: pela mesma razão da fase F4, o contêiner é
`read_only`, não tem o token do Telegram e não deveria ter.

O caminho que combina com a frota é o mesmo do sentinela: um script no host, com
timer, que consulta o portal (por um comando `manage.py` ou uma rota interna) e
chama o `alerta.sh` quando houver solicitação nova. Fica registrado como o
primeiro item depois da publicação.

## 5. Verificação depois de publicar

- as sete rotas respondendo: `/`, `/login`, `/privacidade`, `/contato`
  (POST e OPTIONS), `/contato/recebido`, `/atendimento/`, `/health`;
- um envio real pelo formulário do site, ponta a ponta, chegando à lista;
- um envio com origem errada recebendo 403;
- `manage.py expurgar_contatos --simular` no servidor;
- o backup do banco `mp_portal` aparecendo no ciclo diário e relido com
  `pg_restore --list`;
- o `/health` novo no vigia e no monitor externo.
