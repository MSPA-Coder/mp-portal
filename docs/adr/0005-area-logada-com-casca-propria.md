# ADR 0005 — A área logada tem casca própria, e quem entra é um círculo de confiança

> **Rascunho para revisão — 10/09/2026.** Registra a diretriz nova do
> mantenedor: o portal deixa de ser "site com um anexo interno" e passa a ter
> duas metades com aparência própria, e o punhado de pessoas que entra
> (mantenedor + três) compartilha tudo lá dentro. **Fases 1 a 3 implementadas
> (aguardando revisão para commitar); fases 4 a 6 pendentes.** O plano está ao
> final.
>
> **Desvio da fase 1:** a tela de `/login` **continuou na casca do site**, e
> não na do painel. É a soleira pública -- alcançada pelo item "Login" do menu
> do site, sem sessão --, e a barra do painel não teria o que oferecer a quem
> ainda não entrou. `test_seguranca` já agrupa `/login` com as páginas
> públicas. Mover é cosmético e fica para quando (ou se) fizer diferença.
>
> **Decisões de detalhe já tomadas (10/09/2026):** navegação da área logada é
> **barra no topo** (enxuta, mesma posição do cabeçalho do site); os módulos
> autenticados passam a viver sob o prefixo **`/painel/`** (`/login`,
> `/contato`, `/privacidade`, `/health`, `/robots.txt` e `/sitemap.xml`
> continuam na raiz); o Atendimento **continua restrito a `is_staff`** — a
> "conta designada" é construída dentro desse círculo, e abrir a lista para os
> três fica para quando existir o sistema de perfis, com o aviso de privacidade
> revisto antes (fase 5, adiada).

## Contexto

A ADR 0003 incorporou o site ao portal com **uma casca só** — cabeçalho, menu e
rodapé idênticos para as sete páginas públicas e para as telas com login. O
argumento decisivo foi o menu: "Atendimento" ao lado de "Soluções" obrigava a
não ter duas cópias da casca.

Duas coisas mudaram desde então:

1. **O site é rascunho, o sistema é o produto.** O institucional foi uma
   experiência estática que já cumpriu o papel de existir. O que vai crescer é
   a área logada — hoje tarefas e atendimento, amanhã os serviços que ainda não
   estão definidos.
2. **Quem entra não é "cliente externo".** A diretriz é um gerenciador de
   tarefas para o mantenedor e três pessoas colocarem tarefas umas para as
   outras, no lugar de mensagens de WhatsApp que se perdem. São quatro pessoas
   que já decidem juntas o que cada uma faz. Não é o "cliente" da ADR 0002 —
   é um círculo de confiança.

Com isso, mostrar o menu institucional ("Início", "Soluções", "Método"…) para
quem está dentro do sistema virou ruído: essa pessoa não está ali para navegar
o material comercial, está para trabalhar.

## Decisão

### 1. Duas cascas, um único deploy

A área logada ganha **casca própria** (`templates/app/base.html`): barra
enxuta com as áreas do sistema (Tarefas, Atendimento, Contas), o nome de quem
está logado e "Sair". Sem menu institucional, sem a barra "0800 24h", sem o
botão "Solicitar orçamento".

As sete páginas públicas continuam **intocadas** na casca atual
(`templates/site/base.html`).

Continua **um repositório, uma imagem, um contêiner, um `deploy.sh portal`**.
A separação é de camada de apresentação, não de implantação. Não se justifica
dois serviços num sistema com quatro usuários e uma frota inteira montada em
"um contêiner por app".

### 2. A área logada é compartilhada entre as quatro pessoas

Toda conta autenticada vê e mexe em **todas** as tarefas — é o grupo de
WhatsApp que ela substitui, com histórico. Sem tabela de cliente, sem escopo
por pessoa. A ADR 0002 **não** é disparada: continua não existindo dado
particionado por cliente externo.

O rastro que já existe nas tarefas (cada mudança vira uma linha de andamento
com autor e data) é o que substitui uma matriz de permissão — mesmo argumento
da ADR 0004.

### 3. Contas viram CRUD (tela, não linha de comando)

Hoje conta se cria por `manage.py createsuperuser` no VPS. Com quatro pessoas
que entram e eventualmente mudam, e sem `django.contrib.admin` instalado, isso
significa SSH para cada ajuste. Passa a existir uma tela mínima de contas
(`/contas/`), restrita a `is_staff`: listar, criar, editar, ativar/desativar.
Sem autoatendimento — quem cadastra pessoa é o mantenedor.

### 4. Os módulos autenticados vivem sob `/painel/`

Hoje cada app interno registra sua própria rota na raiz (`/tarefas/`,
`/atendimento/`), e a garantia "tudo aqui exige sessão" é vigilância por app —
o próprio `tarefas/urls.py` anota o cuidado: *"um caminho que começa com
`/tarefas/` está atrás de `somente_equipe`, sem exceção a conferir"*.

Um prefixo comum torna isso **estrutural** em vez de vigiado:

- uma regra só — "abaixo de `/painel/` → sessão obrigatória" — verificável num
  lugar (middleware ou o `include` das rotas), e não relida a cada app novo;
- um ponto único para endurecer na borda: `Cache-Control: no-store` para tudo
  que é autenticado, limite de taxa próprio, e no futuro uma lista de IP ou
  um segundo fator, tudo num `location /painel/` do nginx sem enumerar rota;
- o corte limpo para a expansão da ADR 0002: quando o cliente externo existir,
  ele entra como `/painel/cliente/` ao lado de `/painel/equipe/`, e a casca do
  app já sabe onde ramificar.

`/login` **fica na raiz** — o limite de taxa do nginx central mira exatamente
`POST /login`, e as páginas públicas (`/contato`, `/privacidade`, `/health`,
`/robots.txt`, `/sitemap.xml`) não se movem. Os endereços antigos
(`/tarefas/…`, `/atendimento/…`) respondem 301 para os novos.

### 5. `is_staff` deixa de ser a fronteira "equipe × cliente" e vira "administra × usa"

Enquanto o critério das telas internas era `is_staff` = "equipe da MP", ele
protegia as tarefas de um cliente externo. Agora que as quatro pessoas
compartilham as tarefas, `is_staff` muda de significado: passa a marcar **quem
administra o portal** (mexe em contas) e não **quem pode trabalhar nele**.

- **`/painel/tarefas/`** — `login_required`. As quatro pessoas usam.
- **`/painel/contas/`** — `is_staff`. Só o mantenedor (e quem ele promover).
- **`/painel/atendimento/`** — `is_staff` (ver o item resolvido abaixo).

## Atendimento: quem enxerga os pedidos do formulário — RESOLVIDO

O mantenedor sinalizou querer que todas as contas consultem o atendimento, com
uma conta designada como destinatária. Depois do alerta abaixo, **a decisão foi
manter restrito a `is_staff` por ora**: a conta designada ("responsável pelo
atendimento") é construída dentro desse círculo (fase 4), e abrir a lista para
os três fica para quando existir o sistema de perfis, com o aviso de
privacidade revisto antes (fase 5, adiada).

O alerta, registrado para não se perder: os três não são funcionários da MP, e o
aviso de privacidade publicado hoje diz, com todas as letras, que os dados de
contato **não são compartilhados** ("COMPARTILHAMENTO = Nenhum") e que a
finalidade é "conduzir a tratativa comercial". Abrir a lista de solicitações
— nome, e-mail, telefone e mensagem de terceiros que preencheram o formulário —
para pessoas de fora da MP:

- pode extrapolar a finalidade declarada e a cláusula de não compartilhamento
  (risco LGPD real, não teórico — a aplicação inteira foi desenhada em torno
  desse aviso);
- expõe a carteira de leads comerciais a quem talvez seja de outra empresa.

## O institucional continua caindo junto com a aplicação

A ADR 0003 já aceitou isso e apontou o caminho de volta: cache das páginas
públicas no nginx central, sem desincorporar. A casca própria **não muda** esse
custo — mas reforça que o L06 (medir o RTO) segue pendente e agora mais caro.

## Alternativa considerada e recusada

**Dois deploys** — o site volta a ser estático (ou contêiner próprio), o portal
serve só o sistema. É o que o LEVANTAMENTO §L21 recomendava e a ADR 0003
reverteu. Recusada de novo, pelos mesmos motivos e mais um: agora existiria
também a duplicação do modelo de navegação entre "Login" no site e a barra do
app. Um sistema com quatro usuários não paga o preço de duas pipelines, dois
vhosts de aplicação e a casca partida em duas linguagens para comprar uma
independência de disponibilidade que, medida, provavelmente não é necessária.

## Gatilho de revisão

- **O cliente externo de verdade aparecer.** No dia em que um serviço tiver
  conteúdo que depende de *qual* cliente olha, a ADR 0002 volta à mesa e a área
  logada deixa de ser um espaço compartilhado só — passa a ter `/cliente/` com
  escopo obrigatório, e a casca do app talvez precise de uma terceira variação.
- **Papel dentro do círculo.** Alguém precisar ver sem poder mexer, ou o
  atendimento precisar de dono formal com os outros só de leitura: é o "sistema
  formal de perfis", e é uma decisão própria.

## Plano em fases

Cada fase é um PR pequeno, revisável e reversível sozinho.

| Fase | O que | Risco | Estado |
|---|---|---|---|
| **1 — Casca própria** | `templates/app/base.html` + `app/_barra.html`; mover tarefas (lista/detalhe/formulário) e atendimento (lista/detalhe) para ela; `css/painel.css`; trocar os itens internos do `_topo.html` do site por uma porta só ("Painel"); testes de navegação e de casca | baixo, aditivo | ✅ feito |
| **2 — Prefixo `/painel/`** | `tarefas.urls` e as rotas de atendimento passam para `painel/…`; 301 dos endereços antigos (`_legado_para_painel`); `robots.txt` fecha `/painel/`; `reverse()`/`{% url %}` por nome, então nem views nem templates mudam de corpo | baixo | ✅ feito |
| **3 — `login_required` nas tarefas** | tarefas sai de `somente_equipe` para `login_required`; `equipe()` vira `pessoas()` (toda conta ativa); `apos_login` manda todo mundo para as tarefas; `core/autorizacao.py` passa a guardar só a administração; testes reescritos | baixo | ✅ feito |
| **4 — CRUD de contas** | rotas `/painel/contas/` (lista, criar, editar, ativar/desativar), `is_staff`; sem e-mail (senha definida na tela, com os validadores do Django); testes | médio | pendente |
| **5 — Responsável pelo atendimento** | campo/config de conta designada (`is_staff`); cada `Contato` novo aponta para ela; a lista destaca "as minhas" | médio | pendente |
| **6 — (adiada) abrir atendimento + revisar o aviso** | só se a revisão futura decidir abrir: cláusula de compartilhamento e finalidade no aviso de privacidade, nova versão, e então afrouxar a autorização do atendimento | alto (LGPD) | adiada |

As fases 1–3 saíram num bloco só (é a "virada de casca"). A 4 e a 5 podem
começar quando o mantenedor quiser; a 6 está adiada por decisão dele.
