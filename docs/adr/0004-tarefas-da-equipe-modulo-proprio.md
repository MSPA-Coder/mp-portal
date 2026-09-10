# ADR 0004 — Tarefas da equipe como módulo do portal, e não ferramenta de fora

**Data:** 08/09/2026

## Contexto

O mantenedor precisa acompanhar tarefas com mais duas pessoas: o que fazer, de
quem é, para quando, e como está. A pergunta que abriu a decisão foi se havia
algo pronto no GitHub que servisse.

Há, e são boas: Kanboard, Vikunja, Planka, WeKan — todas auto-hospedáveis, todas
mais completas do que o que se escreve aqui em uma tarde.

## Decisão

**Módulo nativo do portal**, no app `tarefas`, atrás da mesma sessão e da mesma
autorização do atendimento.

## Motivo

Uma ferramenta de fora seria mais capaz e mais cara, e o custo não está na
implantação — está nos quatro lugares em que ela passaria a existir para
sempre:

1. **Outra base para salvar.** O `BackupRestore` já cobre o PostgreSQL deste
   portal; um segundo serviço com estado é uma segunda origem a catalogar,
   verificar e restaurar.
2. **Outro login.** A `SharedAuth` unificou a autenticação dos aplicativos da
   frota. Casar o SSO de uma ferramenta de terceiro com ela é trabalho real, e
   a alternativa — deixar um segundo login solto — é exatamente o que o portal
   recusa ao não instalar `django.contrib.admin`.
3. **Outro ciclo de atualização.** Mais um contêiner cuja versão precisa ser
   acompanhada, com CVE próprio e política de dependência própria.
4. **Outra casca.** O portal tem uma casca só — foi o motivo de incorporar o
   site (ADR 0003). Uma ferramenta de fora dentro de um `iframe` seria a
   segunda, e um link para outro domínio seria sair do produto.

Contra isso, o que o módulo nativo precisa ter é pequeno: duas tabelas, um CRUD
e uma linha do tempo. A troca só compensa porque o escopo é honestamente
pequeno — **três pessoas**, sem cliente externo olhando, sem dependência,
subtarefa, quadro configurável ou anexo. No dia em que o escopo crescer para
perto do que um Vikunja entrega, esta decisão volta à mesa em vez de o módulo
crescer até virar um clone pior.

## O que o módulo deliberadamente não tem

- **Percentual de conclusão.** As cinco situações já dizem onde a tarefa está, e
  "70%" é uma opinião que ninguém confere.
- **Exclusão.** Tarefa errada vira `CANCELADA` e o registro fica. Diferente do
  `Contato`, onde a exclusão existe porque a LGPD dá esse direito ao titular,
  aqui apagar destruiria o único histórico de uma decisão da equipe.
- **Anexo.** O portal não recebe upload (`FILE_UPLOAD_MAX_MEMORY_SIZE = 0`).
  Abrir essa porta é decisão de infraestrutura, não de tela.
- **Permissão por pessoa dentro da equipe.** Quem entra vê e mexe em tudo. São
  três pessoas que já decidem juntas quem faz o quê; uma matriz de permissão
  seria estrutura sem leitor — o mesmo argumento do ADR 0002. O que existe no
  lugar é rastro: toda mudança de situação e toda troca de responsável viram
  uma linha de andamento com autor e data.

## Autorização: `is_staff`, e não "autenticado"

O ADR 0002 registra que a área do cliente vai existir, e a conta de cliente
será autenticada também. Se o critério aqui fosse a sessão, o dia em que o
primeiro cliente entrasse seria o dia em que ele passaria a ler as tarefas
internas da MP.

A regra saiu de dentro de `contatos/views.py` e subiu para
`core/autorizacao.py` quando a segunda área apareceu: duas cópias da mesma
decisão de autorização divergem no dia em que uma delas for corrigida.

## Gatilhos de revisão

- **Papel dentro da equipe.** O ADR 0002 já previa este gatilho — "mais de uma
  pessoa operando o atendimento" — e ele agora disparou pela metade: são três
  pessoas, mas todas com o mesmo papel e por escolha. Vira decisão de verdade
  quando alguém precisar ver sem poder mexer.
- **Escopo além de três pessoas ou além de uma lista.** Dependência entre
  tarefas, recorrência, anexo, cliente externo enxergando o andamento: qualquer
  um destes torna a comparação com uma ferramenta pronta favorável de novo.
