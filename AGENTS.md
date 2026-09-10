# MP Portal — orientações de trabalho

## Escopo

Aplicação Django que é, ao mesmo tempo, o **site institucional** da MP Soluções
Corporativas (sete páginas públicas) e o **sistema** por trás dele (formulário
de contato com destino, área autenticada). Uma aplicação, um repositório, um
domínio — ver `docs/adr/0003-site-incorporado-ao-portal.md`, que registra a
incorporação e o que ela reverteu.

A área autenticada tem duas telas hoje: **atendimento** (as solicitações
vindas do site) e **tarefas** (o que a equipe de três pessoas combinou de
fazer — ver `docs/adr/0004-tarefas-da-equipe-modulo-proprio.md`, que registra
por que é módulo daqui e não ferramenta de fora).

Fontes de verdade, nesta ordem: o código, este arquivo, o `README.md`,
`docs/operacao.md`, `docs/adr/` e o repositório `manutencao` para a
infraestrutura compartilhada do VPS.

**Nada disto está publicado.** Em produção, quem atende hoje é o site estático
do repositório `MpSolucoes`. A virada é um passo próprio, descrito em
`docs/operacao.md`, e aciona três decisões adiadas (L06, L19 e L11 da §6 do
levantamento).

## Invariantes

### Do site que veio para cá

- **Uma casca só.** Cabeçalho, rodapé e menu existem uma vez, em
  `templates/site/_topo.html` e `_rodape.html`, e valem para as páginas
  públicas E para as telas autenticadas. Foi o motivo da incorporação; não
  crie uma segunda.
- **Uma fonte para os metadados.** Título, descrição, imagem, rótulo de menu e
  linha do sitemap saem de `institucional/paginas.py`. Página nova = entrada
  nessa tabela + template + rota. Há teste comparando os três lugares.
- **O domínio não aparece em arquivo nenhum.** `canonical`, `og:url`, `robots` e
  `sitemap` saem do request. Trocar de domínio é zero edição aqui — propriedade
  conquistada na fase F5 e preservada. Não escreva o domínio em template, em
  configuração nem em teste.
- **Autossuficiência.** Nada em `static/site/` pode referenciar host externo
  (CDN, fonte remota, imagem remota). Fontes e imagens são vendorizadas. Há
  teste que reprova.
- **URL limpa, uma página um documento.** `/solucoes`, nunca `/solucoes.html` —
  a forma com extensão responde 301 e existe só porque já foi indexada.
- **As páginas públicas não consultam o banco.** É o que mantém o institucional
  servível quando o PostgreSQL não responde, e é o que reduz o custo de o site
  ter passado a depender da aplicação. Há teste.

### Do portal

- **Uma linha de `contatos_contato` é dado pessoal de terceiro.** Toda mudança
  no modelo passa por `contatos/privacidade.py`: o aviso declara campo a campo
  o que é guardado, e a suíte compara os conjuntos. Campo novo sem linha no
  aviso reprova a CI — é assim que se evita um aviso que virou mentira.
- **Consentimento é restrição de banco**, não validação de formulário
  (`CheckConstraint contato_exige_consentimento`).
- **O endereço IP não é guardado.** Só o HMAC dele com o `SECRET_KEY`
  (`contatos/limites.py`). Não acrescente coluna com IP em claro.
- **`/contato` responde GET e POST na mesma rota**, com CSRF normal. A isenção
  que existiu enquanto o formulário morava fora foi revertida — ver ADR 0001.
  **Não reintroduza `@csrf_exempt` em nenhuma view.**
- **Com `USE_HTTPS=True` a aplicação recusa subir** sem `CSRF_TRUSTED_ORIGINS` e
  sem `CONTATO_CANAL_TITULAR` (`contatos/checks.py`). O gatilho é `USE_HTTPS` e
  não `DEBUG`, porque `DEBUG=False` também vale no build e na suíte.
- **CSP estrita**: `default-src 'self'`, de `sharedauth.security.montar_csp()`,
  com **uma** folga — `img-src data:`, pelo SVG de ruído do `site.css`. Nada de
  `<style>`/`<script>` embutido nem atributo `style=`; estilo pontual vira
  classe. Há teste que reprova uma segunda ocorrência de `data:`.
- **`django.contrib.admin` não entra.** Registraria o modelo de usuário e
  abriria um segundo login, fora do `/login` que o nginx central limita.
- **Destino pós-login é derivado da conta** (`contas/views.py`), nunca fixo. É a
  emenda por onde a área do cliente entra — ver ADR 0002.
- **Quem entra na área interna é `is_staff`**, e a regra mora em UM lugar:
  `core/autorizacao.somente_equipe`. Não recrie o decorador dentro de um app, e
  não troque o critério por "autenticado" — a conta de cliente que o ADR 0002
  prevê também será autenticada.
- **No menu, `Login` é para quem não entrou** e as áreas internas são para quem
  entrou (`templates/site/_topo.html`). Mostrar "Login" a quem já tem sessão
  sugere que ela caiu — a mesma razão pela qual o 403 do atendimento não
  devolve ninguém à tela de login.
- **Rota nova sob sessão entra no `robots.txt`.** Toda área autenticada é
  `Disallow`; para o robô, cada visita vira um desvio para o login.
- **Em `tarefas`, `situacao` e `concluida_em` mudam juntas**, pelo
  `Tarefa.aplicar_situacao`. A restrição `tarefa_conclusao_coerente` recusa a
  divergência no banco — não escreva `situacao` direto.
- **`/health` responde com e sem barra**, com o corpo
  `{"servico": "mp-portal", "status": ...}`. O `deploy.sh` e o vigia dependem
  desse formato.

### Do repositório

- **A suíte toca o banco.** Achado L01 do levantamento. Teste novo que verifique
  persistência, restrição ou migração usa `pytest.mark.django_db` — não
  `inspect.getsource`, não leitura de arquivo.
- **App novo é app novo em quatro lugares**: `INSTALLED_APPS`, `COPY` nos dois
  estágios do `Dockerfile`, `packages` do `pyproject.toml` e a fronteira do
  runtime na CI. Esquecer o `COPY` faz a suíte passar e a imagem servida morrer
  no arranque — aconteceu com o `institucional`.
- **LF, sem BOM**, em todo arquivo. `.gitattributes` força.
- **Acento em texto de interface, nunca em identificador.** Rótulo exibido,
  mensagem e documento levam acento; nome de campo, código de `TextChoices`,
  chave de dicionário, nome de teste e token de log são ASCII.
  **Consequência em modelo Django:** o rótulo padrão é derivado do nome do
  atributo, que é ASCII por esta mesma regra — então campo que aparece em
  formulário precisa de `verbose_name` explícito, ou a tela mostra "Descricao".
  Aconteceu em `tarefas`, passou pela suíte inteira e só apareceu no navegador.
- **Comentário de template em várias linhas é `{% comment %}`**, nunca
  `{# #}` — a forma com cerquilha só vale em uma linha, e escrita em duas o
  texto sai no HTML. Há teste procurando sintaxe vazada.

## Portas

`5601` (aplicação) e `5602` (PostgreSQL), publicadas só em `127.0.0.1`.
Numeração da frota: megasena 51xx, bancário 52xx, renda e conforto 50xx, site
estático 55xx, portal 56xx.

## Suíte

```bash
docker compose --profile quality run --build --rm quality
```

O `--build` **não é opcional**: sem ele a suíte roda sobre a imagem anterior.

Diante de vermelho, decida de quem é o defeito antes de mexer: teste que mede
texto literal reprova mudança legítima, e nesse caso quem se corrige é a
asserção. Nunca escreva código para o teste passar.

E rode no navegador antes de considerar pronto. Os dois defeitos mais caros
desta construção — o comentário de template vazando no `<head>` e o app novo
faltando na imagem servida — passaram pela suíte inteira e só apareceram
abrindo a aplicação.

## Dependências

Faixa no `pyproject.toml` (contrato de compatibilidade, lido pelo Dependabot) e
versão exata no `uv.lock` (o que é testado e servido). Não troque faixa por
`==`. A política da casa é alargar o teto e preservar o piso.

`sharedauth` vem por referência Git, fixada em tag, **sem o extra `[flask]`**.

O lock se regenera em contêiner (não há `uv` no host):

```bash
docker run --rm -v "${PWD}:/w" -w /w python:3.14-slim \
  sh -c "apt-get update -qq && apt-get install -y -qq git && pip install -q uv==0.12.10 && uv lock"
```

## Conteúdo institucional

As sete páginas vieram do repositório `MpSolucoes` byte a byte, pelo script
registrado no commit da incorporação. Se precisar refazer a migração, o
conteúdo original continua lá até o repositório ser arquivado.

Imagens novas entram como `webp` (qualidade ~82, largura máx. 1600), com
`width`/`height` declarados e `loading="lazy"` abaixo da dobra — sem isso a
página salta enquanto carrega, que é critério de Core Web Vitals.
