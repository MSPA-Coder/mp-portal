# ADR 0001 — `POST /contato` sem CSRF, com lista de origens

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
