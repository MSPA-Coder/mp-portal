# ADR 0002 — Sem modelo de cliente enquanto não houver módulo que o use

> **Atualizada em 08/09/2026.** O destino deixou de ser hipótese: o mantenedor
> declarou que a área autenticada terá **dois públicos em áreas separadas** —
> clientes e equipe da MP. Isso não muda a decisão de não criar a tabela agora
> (continua sem módulo que a leia), mas muda duas coisas: o gatilho ficou mais
> perto, e a **emenda** por onde a segunda área entra já foi construída — o
> destino pós-login é derivado da conta (`contas/views.py`), não um endereço
> fixo. Ver "Emenda já construída", ao final.

## Decisão

O portal nasce **sem** tabela de cliente e sem vínculo entre `UsuarioPortal` e
cliente. `contas.UsuarioPortal` é uma subclasse vazia de `AbstractUser`, e a
única autorização existente é `is_staff`, que separa "equipe da MP Soluções Corporativas" de
"qualquer outra conta".

O que existe já é multiusuário no sentido óbvio (várias contas, sessão por
conta, autorização por rota). O que **não** existe é dado particionado por
cliente.

## Motivo

A F7 do `LEVANTAMENTO_2026-09.md` prevê que o portal seja "multiusuário de
verdade, com dados por cliente", e o achado L21 observa, com razão, que ele é
o consumidor que faltava para justificar o plano de multiusuário e permissões
registrado em 24/08.

Só que nesta rodada o portal tem exatamente um tipo de dado — a solicitação de
contato — e ela **não pertence a um cliente**: pertence a um visitante que
ainda não é cliente nenhum. Uma tabela `Cliente` criada agora não teria uma
única consulta que a lesse. Estrutura sem consumidor é especulação: ela envelhece
errado, porque a forma certa só aparece quando o primeiro módulo real diz de
que jeito o dado precisa ser filtrado.

`AUTH_USER_MODEL` é a exceção deliberada a esse raciocínio, e por um motivo
mecânico: trocá-lo depois da primeira migração é recriar o schema. O custo hoje
é uma classe vazia; o custo depois é uma migração de dados. As duas coisas não
se comparam.

## Alternativa considerada e recusada, por ora

`Cliente` (razão social, documento, contato) mais `UsuarioPortal.cliente` como
chave estrangeira nulável, já na primeira migração. Recusada porque as três
decisões que dão forma a esse modelo continuam em aberto: o que o cliente vê
quando entra, se uma conta pertence a um cliente ou a vários, e se o acesso é
por pessoa ou por empresa. Nenhuma delas se responde escrevendo código.

## Gatilho de revisão

**O primeiro módulo com dado por cliente** — documentos, chamados, ocorrências
ou indicadores, o que vier primeiro. No momento em que existir uma tela cujo
conteúdo depende de *qual* cliente está olhando, esta decisão volta à mesa, e
com ela o plano faseado de 24/08.

## Forma recomendada, quando o gatilho disparar

Registrada aqui para não ser redescoberta:

1. `Cliente` como tabela própria, e **chave estrangeira obrigatória** em todo
   modelo de domínio — nulável convida a linha órfã, que é o vazamento clássico
   entre inquilinos;
2. um *manager* padrão que exija o escopo, de modo que `Modelo.objects.all()`
   sem cliente seja erro de programação e não uma consulta que devolve o acervo
   inteiro;
3. **um teste por modelo** provando que uma conta de um cliente não alcança
   linha de outro — teste de banco, não de leitura de código;
4. a diferença em relação aos irmãos precisa ficar escrita: no MegaSena
   "qualquer conta autenticada acessa o acervo comum" (ADR 0002 de lá) e isso é
   deliberado. Aqui não pode ser.

## Fora de escopo

Esta decisão não trata de papéis dentro da equipe da MP Soluções Corporativas. Hoje há dois
níveis (`is_staff` e o resto) e isso basta para uma lista de solicitações
operada por uma pessoa. Papel granular é outra decisão, com outro gatilho: mais
de uma pessoa operando o atendimento.

---

## Emenda já construída — 08/09/2026

Como a área do cliente é destino declarado, a única parte que seria cara de
acrescentar depois foi feita agora: **para onde cada conta vai depois de
entrar**.

`LOGIN_REDIRECT_URL` aponta para `/apos-login`, e essa view decide pela conta —
hoje, `is_staff` vai para `/atendimento/` e qualquer outra volta ao site. No dia
em que a área do cliente existir, muda-se uma função e nenhum template, menu ou
teste de navegação precisa ser reescrito.

É o mesmo padrão do ControleBancario, e pelo mesmo motivo escrito lá: destino
fixo obriga a tela de destino a não exigir permissão nenhuma, o que é uma
restrição estranha para uma tela de produto.

**O que continua não existindo, e não deve ser inventado antes da hora:** conta
de cliente, vínculo entre conta e empresa, e qualquer tela sob `/cliente/`. O
gatilho continua sendo o primeiro módulo com dado por cliente, e a forma
recomendada continua sendo a das quatro linhas acima.
