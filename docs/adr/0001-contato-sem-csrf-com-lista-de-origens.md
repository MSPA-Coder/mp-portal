# ADR 0001 — `POST /contato` sem CSRF, com lista de origens

> **REVERTIDA EM 08/09/2026, pelo gatilho que ela própria escreveu.** O site
> institucional foi incorporado ao portal (ADR 0003), formulário e destino
> passaram a ser a mesma origem, e o custo do token CSRF caiu a zero. A rota
> voltou a ser protegida pelo CSRF do Django; `contatos/origens.py`, o CORS, o
> pré-voo e a verificação `contatos.E002` foram removidos. O texto abaixo fica
> como estava, porque o registro de por que a decisão fez sentido é o que
> permite julgar se a reversão faz. Ver a seção final.

## Decisão

A rota `POST /contato` é a única do portal marcada com `@csrf_exempt`. No lugar
do token CSRF, ela é protegida por quatro controles, nesta ordem de execução:

1. **lista de origens** (`contatos/origens.py`) — o cabeçalho `Origin` precisa
   estar em `CONTATO_ORIGENS_PERMITIDAS`, por comparação exata. Lista vazia
   recusa tudo fora do modo de depuração;
2. **limite por origem de rede** (`contatos/limites.py`) — 5 envios por 15
   minutos por HMAC de endereço, contados na própria tabela;
3. **campo-armadilha** (`contatos/forms.py`) — preenchido, a resposta é
   idêntica à de sucesso e nada é gravado;
4. **corpo pequeno** — `DATA_UPLOAD_MAX_MEMORY_SIZE` em 128 KiB e teto por
   campo de texto.

Nenhuma outra view do projeto é isenta de CSRF. A área de atendimento usa o
CSRF do Django normalmente, e há teste que reprova POST sem token.

## Motivo

O formulário mora no site institucional, que é **estático** e pode estar em
outra origem. Um token CSRF exigiria uma ida e volta só para buscá-lo, e
guardá-lo num cookie em página estática servida por nginx sem aplicação é
inventar sessão onde não há.

Mais importante que a mecânica: **CSRF defende contra ação executada em nome de
quem está autenticado**. Nesta rota não há sessão, não há ninguém autenticado e
não há ação a executar em nome de alguém — o pior que um terceiro consegue é
criar um pedido de contato falso, que é exatamente o que o limite de taxa e o
campo-armadilha tratam.

O `Origin` é a peça que sustenta a decisão: o navegador o envia em todo POST,
de mesma origem ou não (Fetch Standard), e **a página não pode forjá-lo**. Uma
lista de origens é, para esta rota, a mesma garantia que o token daria — sem
estado.

## Alternativas consideradas e recusadas

| Alternativa | Por que não |
|---|---|
| Serviço de formulário (Formspree, Basin) | O dado pessoal sairia para terceiro, e entraria no aviso de privacidade como compartilhamento. Foi recusado no achado L20 do levantamento. |
| `mailto:` | Conversão péssima e expõe o e-mail a coletor. Também recusado no L20. |
| Buscar token em `GET /contato/token` antes de enviar | Duas requisições e uma dependência de JavaScript para a única coisa que precisa funcionar sem ele. Não protege mais do que a lista de origens. |
| Servir o formulário pelo portal | Tiraria a página de contato do site estático e a colocaria atrás de uma aplicação — mais superfície, pior desempenho, e o site perderia a autonomia que a fase F5 lhe deu. |

## Gatilho de revisão

**A primeira rota pública que faça mais do que gravar um pedido de contato.**
Se um dia `POST /contato` (ou uma irmã dela) passar a autenticar, alterar dado
existente, disparar cobrança ou enviar mensagem em nome de alguém, o raciocínio
acima deixa de valer — a partir daí existe ação em nome de alguém, e o token
volta a ser necessário.

Gatilho secundário: se o site deixar de ser estático e passar a ser servido pela
mesma aplicação, o custo do token cai a zero e não há mais motivo para a
isenção.

## Fora de escopo

Esta decisão não afeta a área de atendimento, o login, nem qualquer rota
autenticada. `SESSION_COOKIE_SAMESITE = "Lax"` continua valendo e é o que
impede que o cookie do portal seja enviado por uma página de terceiro.

---

## Reversão — 08/09/2026

O gatilho secundário desta ADR dizia: *"se o site deixar de ser estático e
passar a ser servido pela mesma aplicação, o custo do token cai a zero e não há
mais motivo para a isenção"*. Foi exatamente o que aconteceu (ADR 0003).

**O que saiu:** `contatos/origens.py`, a configuração
`CONTATO_ORIGENS_PERMITIDAS`, os cabeçalhos de CORS, o tratamento de `OPTIONS`,
a verificação `contatos.E002` e a aceitação de corpo JSON — que existia para
servir um `fetch` de outra origem que não existe mais.

**O que entrou no lugar:** nada de novo. O `CsrfViewMiddleware` do Django, que
já protegia todas as outras rotas, passou a proteger também esta. Um teste
exercita o caminho com `enforce_csrf_checks` ligado, e ele reprova o envio sem
token.

**O que permaneceu, porque nunca foi sobre CSRF:** o campo-armadilha, o limite
por resumo de endereço de rede, o corpo pequeno e o consentimento como
restrição de banco. Eles defendem contra abuso e spam, não contra requisição
forjada — e abuso continua existindo depois da incorporação.

**Se um dia o formulário voltar a morar fora desta aplicação** — um parceiro
embutindo o formulário no site dele, por exemplo —, esta ADR volta a valer
inteira, e o histórico de por que ela funcionava está preservado acima.
