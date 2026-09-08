# Operação: a virada, e o que ela aciona

O portal **não está publicado**. Em produção, quem atende `mp-solucoes` hoje é
o site estático do repositório `MpSolucoes`, servido por nginx na porta 5501.
Publicar este repositório não é instalar um serviço novo: é **substituir um
serviço que está no ar**.

Este documento é a lista do que falta, na ordem, para que o dia da virada seja
uma execução e não uma redescoberta.

## 0. Antes de qualquer coisa: três decisões voltam à mesa

A §6 do `LEVANTAMENTO_2026-09.md` registra cinco riscos aceitos, cada um com o
gatilho que deve fazer a decisão ser revisitada. **A virada dispara três.**

| Achado | O que estava aceito | Por que dispara agora |
|---|---|---|
| **L06** — RTO nunca medido | Sabe-se que o dump restaura; não se sabe em quanto tempo o ambiente inteiro volta. | O gatilho é literal: *"antes de o portal do cliente entrar no ar"*. E agora vale mais: depois da incorporação, **o site institucional cai junto com a aplicação**. Um site fora do ar é cliente que não chega. |
| **L19** — DuckDNS | Sufixo compartilhado, sem autoridade de domínio, sem e-mail corporativo. | O domínio próprio já está a caminho. Ele destrava o e-mail no domínio (encaminhamento gratuito resolve) e o canal do titular exigido pela LGPD, que hoje não tem endereço. |
| **L11** — `mp-solucoes` sem branch protection | `main` aceita force-push, sem status check obrigatório. | O que se aceita para um site estático não é o que se aceita para um repositório cujo defeito derruba o site **e** vaza dado pessoal de terceiro. |

## 1. Medir o RTO antes (L06)

Não é burocracia: a incorporação transferiu o site institucional para dentro de
uma aplicação com banco. Antes da virada, vale saber quanto tempo leva para
reconstruir o ambiente do zero e se o `KIT_RECUPERACAO.md` está correto. É a
diferença entre "o site voltou em 20 minutos" e "o site voltou quando deu".

## 2. Infraestrutura no repositório `manutencao`

Editar `vps/` lá **não implanta nada** — a cópia do servidor é a que roda.
Depois de mudar: `bash vps/instalar.sh` no VPS e conferir com `--check`.

- **vhost**: o host público passa a apontar para `127.0.0.1:5601` em vez de
  `:5501`. O limite de taxa de `POST /login` do `conf.d/00-comum.conf` já pega o
  portal de graça — a rota chama `/login` exatamente por isso.
- **`deploy.sh`**: verbo `portal` entra; o verbo `mp` sai **depois** de a virada
  estar verificada, não antes — enquanto os dois existirem, voltar atrás é
  trocar uma linha do vhost.
- **`backup-db.sh`**: o banco `mp_portal` entra no ciclo diário. É o primeiro
  banco da frota com dado pessoal de terceiro; vale reler a retenção dos dumps
  à luz disso.
- **`vigia.sh`** e **`uptimerobot-monitores.sh`**: o `/health` do portal entra;
  o do site sai junto com o serviço.
- **sentinela** e **autocura** cobrem o portal sem mudança nenhuma.
- **timer do expurgo**: `manage.py expurgar_contatos` precisa rodar sozinho, ou
  o prazo declarado no aviso de privacidade é promessa que ninguém cumpre.
  Diário, no formato dos outros timers.

## 3. Segredos e variáveis no VPS

Dois arquivos em `.secrets/` (`django_secret_key`, `postgres_password`) e, no
`.env.docker`:

```
USE_HTTPS=True
ALLOWED_HOSTS=<host público>
CSRF_TRUSTED_ORIGINS=https://<host público>
CONTATO_PROXIES_CONFIAVEIS=<rede do nginx central>
CONTATO_CANAL_TITULAR=<endereço para o titular>
```

Com `USE_HTTPS=True` e o canal ausente, **a aplicação recusa subir**. É
deliberado: um aviso de privacidade que promete um canal inexistente é pior que
não ter aviso.

`CONTATO_PROXIES_CONFIAVEIS` importa mais do que parece: sem ela, o limite de
envios conta todo o tráfego como vindo do nginx central — um só balde para
todos os visitantes.

## 4. O que **não** é mais necessário

Estas tarefas existiam enquanto o site e o portal eram dois. A incorporação as
eliminou, e ficam registradas para que ninguém as procure:

- ligar o formulário do site ao endpoint do portal;
- renomear campos do formulário no outro repositório;
- afrouxar `form-action` ou `connect-src` na CSP do site;
- configurar lista de origens, CORS e pré-voo.

## 5. Dados que faltam antes de divulgar

- **Telefone, WhatsApp e e-mail comercial reais**, hoje mascarados com
  asteriscos em `templates/site/_rodape.html` e `templates/site/contato.html`
  (achado L16). Publicar contato falso é pior que não publicar.
- **Canal do titular** para o aviso de privacidade. Com o domínio próprio, um
  alias encaminhado (`privacidade@`) resolve sem custo mensal.

## 6. O aviso de chegada

Quando uma solicitação entra, **nada avisa ninguém** — ela fica na lista até
alguém abrir. É conhecido, e a solução não é um `EmailBackend` dentro do
contêiner: pela mesma razão da fase F4, ele é `read_only`, não tem o token do
Telegram e não deveria ter.

O caminho que combina com a frota é o do sentinela: um script no host, com
timer, que consulta o portal (por um comando `manage.py` ou rota interna) e
chama o `alerta.sh` quando houver solicitação nova. É o primeiro item depois da
publicação.

## 7. Verificação depois da virada

- as sete páginas institucionais em 200, e os seis `.html` em 301;
- `/contato` mostrando o formulário, e um envio real chegando à lista;
- um envio sem token CSRF recusado;
- `/privacidade` acessível pelo rodapé, com o canal do titular preenchido;
- `/atendimento/` pedindo login para quem não tem sessão;
- `robots.txt` e `sitemap.xml` com o **domínio novo**, sem nenhuma edição no
  repositório — é a prova de que a propriedade da F5 sobreviveu;
- `/health` no vigia e no monitor externo;
- o backup do banco `mp_portal` no ciclo diário, relido com `pg_restore --list`;
- `manage.py expurgar_contatos --simular` no servidor.

## 8. Depois de tudo verificado

Arquivar o repositório `MpSolucoes` (arquivar, não apagar: o histórico da F5
continua legível), remover o verbo `mp` do `deploy.sh` e podar a imagem antiga.
