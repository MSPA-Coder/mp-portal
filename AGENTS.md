# MP Portal — orientações de trabalho

## Escopo

Aplicação Django que é, ao mesmo tempo, o **site institucional** da MP Soluções
Corporativas (sete páginas públicas) e o **sistema** por trás dele: o formulário
de contato com destino e o **painel** autenticado em `/painel/`. Uma aplicação,
um repositório, um domínio — ver `docs/adr/0003-site-incorporado-ao-portal.md`.

O painel tem três áreas: **tarefas** (o quadro que o mantenedor e mais três
pessoas compartilham — ADR 0004), **atendimento** (as solicitações vindas do
site, com responsável) e **contas**. Quem entra é um círculo de confiança, e a
área logada tem casca própria — ADR 0005.

O portal **está em produção** em `mp-solucoes.duckdns.org`, num VPS dedicado,
com a mesma infraestrutura do repositório `manutencao` que atende os outros
aplicativos. Operação e pendências em `docs/operacao.md`.

Fontes de verdade, nesta ordem: o código, este arquivo, o `README.md`,
`docs/operacao.md`, `docs/adr/` e o repositório `manutencao` para a
infraestrutura dos VPS.

## Invariantes

### Site público

- **Duas cascas, cada uma com a sua fonte.** O site usa
  `templates/site/_topo.html` e `_rodape.html`; o painel usa
  `templates/app/base.html` (ADR 0005). Rota interna nova entra sob `/painel/`,
  na casca do painel.
- **Uma fonte para os metadados.** Título, descrição, imagem, rótulo de menu e
  linha do sitemap saem de `institucional/paginas.py`. Página nova = entrada
  nessa tabela + template + rota. Há teste comparando os três lugares.
- **O domínio não aparece em arquivo nenhum.** `canonical`, `og:url`, `robots` e
  `sitemap` saem do request, então trocar de domínio é zero edição aqui.
- **Recurso externo é exceção declarada, não proibição.** Por padrão, fontes e
  imagens de `static/site/` são vendorizadas, e há teste que reprova referência
  a host externo — é o que mantém a CSP fechada e o visitante longe de
  rastreamento de terceiros. Quando um recurso externo fizer sentido (vídeo,
  mapa, analytics), ele entra: ajuste a CSP e o teste na mesma mudança e
  registre o motivo — inclusive no aviso de privacidade, se o terceiro receber
  dado do visitante.
- **URL limpa, uma página um documento.** `/solucoes`; a forma `/solucoes.html`
  responde 301 porque já foi indexada.
- **As páginas públicas não consultam o banco.** O institucional continua
  servível quando o PostgreSQL não responde. Há teste.

### Dados e segurança

- **Uma linha de `contatos_contato` é dado pessoal de terceiro.** Toda mudança
  no modelo passa por `contatos/privacidade.py`: o aviso declara campo a campo
  o que é guardado, e a suíte compara os conjuntos. Campo novo sem linha no
  aviso reprova a CI.
- **Consentimento é restrição de banco**, não validação de formulário
  (`CheckConstraint contato_exige_consentimento`).
- **O endereço IP não é guardado em claro** — só o HMAC dele com o `SECRET_KEY`
  (`contatos/limites.py`).
- **`/contato` responde GET e POST na mesma rota**, com CSRF normal. A isenção
  que existiu enquanto o formulário morava em outro site foi revertida (ADR
  0001); nenhuma view usa `@csrf_exempt`.
- **Com `USE_HTTPS=True` a aplicação recusa subir** sem `CSRF_TRUSTED_ORIGINS` e
  sem `CONTATO_CANAL_TITULAR` (`contatos/checks.py`). O gatilho é `USE_HTTPS` e
  não `DEBUG`, porque `DEBUG=False` também vale no build e na suíte.
- **CSP estrita**: `default-src 'self'`, de `sharedauth.security.montar_csp()`.
  A folga atual é `img-src data:`, pelo SVG de ruído do `site.css`; estilo e
  script ficam em arquivo, não embutidos. Folga nova é permitida quando houver
  motivo: acrescente-a com a justificativa e atualize o teste que as confere.
- **Sem `django.contrib.admin`, por decisão.** Ele registraria o modelo de
  usuário e abriria um segundo login, fora do `/login` que o nginx limita; as
  contas são geridas em `/painel/contas/`. Revisitar se aparecer cadastro que
  não compense construir no painel — e, nesse caso, pôr o admin atrás do mesmo
  limitador.
- **Destino pós-login é derivado da conta** (`contas/views.py`). É a emenda por
  onde a área do cliente externo entra — ver ADR 0002.
- **Duas fronteiras de autorização, cada regra num lugar só:**
  `/painel/tarefas/` é `login_required` (o círculo compartilha o quadro);
  `/painel/atendimento/` e `/painel/contas/` são `is_staff`, por
  `core/autorizacao.somente_equipe`. `is_staff` significa "administra o
  portal"; a conta de cliente externo do ADR 0002 ainda não existe.
- **No menu do site, `Login` é para quem não entrou** e `Painel` para quem
  entrou (`templates/site/_topo.html`) — as áreas do sistema ficam na barra do
  painel. Mostrar "Login" a quem já tem sessão sugere que ela caiu.
- **`/painel/` inteiro é `Disallow` no `robots.txt`.**
- **Em `tarefas`, `situacao` e `concluida_em` mudam juntas**, por
  `Tarefa.aplicar_situacao`; a restrição `tarefa_conclusao_coerente` recusa a
  divergência no banco.
- **`/health` responde com e sem barra**, com o corpo
  `{"servico": "mp-portal", "status": ...}`. O `deploy.sh` e o vigia dependem
  desse formato.

### Repositório

- **A suíte toca o banco.** Teste de persistência, restrição ou migração usa
  `pytest.mark.django_db` contra o PostgreSQL efêmero do `quality`.
- **App novo** entra em `INSTALLED_APPS` e em `packages` do `pyproject.toml` — o
  build do wheel reprova se faltar. O `Dockerfile` copia a árvore inteira
  (`COPY . .`), e o que fica fora da imagem é decidido só pelo `.dockerignore`.
  Acrescente o app também à fronteira do runtime na CI (`require_read_only`).
- **LF, sem BOM**, em todo arquivo. `.gitattributes` força.
- **Acento em texto de interface, nunca em identificador.** Rótulo exibido,
  mensagem e documento levam acento; nome de campo, código de `TextChoices`,
  chave de dicionário, nome de teste e token de log são ASCII.
  **Consequência em modelo Django:** o rótulo padrão é derivado do nome do
  atributo, que é ASCII por esta mesma regra — então campo que aparece em
  formulário precisa de `verbose_name` explícito, ou a tela mostra "Descricao".
- **Comentário de template em várias linhas é `{% comment %}`** — a forma
  `{# #}` só vale em uma linha, e escrita em duas o texto sai no HTML. Há teste
  procurando sintaxe vazada.

## Portas

`5601` (aplicação) e `5602` (PostgreSQL), publicadas só em `127.0.0.1`.
Numeração dos aplicativos: megasena 51xx, bancário 52xx, renda 53xx, conforto
50xx (local) e 54xx (VPS), portal 56xx.

## Suíte

```bash
docker compose --profile quality run --build --rm quality
```

O `--build` **não é opcional**: sem ele a suíte roda sobre a imagem anterior.

O que merece teste, em que camada e em que forma está em `docs/TESTES.md`,
comum aos repositórios; leia antes de escrever ou remover um teste.

Diante de vermelho, decida de quem é o defeito antes de mexer: teste que mede
texto literal reprova mudança legítima, e nesse caso quem se corrige é a
asserção. Nunca escreva código para o teste passar.

E rode no navegador antes de considerar pronto: defeitos de template e de
imagem já passaram pela suíte inteira e só apareceram abrindo a aplicação.

## Dependências

Faixa no `pyproject.toml` (contrato de compatibilidade) e versão exata no
`uv.lock` (o que é testado e servido). A política da casa é alargar o teto e
preservar o piso. O Dependabot acompanha o `uv.lock` pelo ecossistema `uv`.

`sharedauth` vem por referência Git, fixada em tag, **sem o extra `[flask]`**.

O lock se regenera em contêiner (não há `uv` no host):

```bash
docker run --rm -v "${PWD}:/w" -w /w python:3.14-slim \
  sh -c "apt-get update -qq && apt-get install -y -qq git && pip install -q uv==0.12.10 && uv lock"
```

## Conteúdo institucional

As sete páginas vieram, byte a byte, do repositório `MpSolucoes`, removido em
10/09/2026; o histórico dele está no bundle `mp-solucoes-f5-arquivo.bundle`, em
`Dropbox/Programacao/`.

Imagens novas entram como `webp` (qualidade ~82, largura máx. 1600), com
`width`/`height` declarados e `loading="lazy"` abaixo da dobra — sem isso a
página salta enquanto carrega, que é critério de Core Web Vitals.
