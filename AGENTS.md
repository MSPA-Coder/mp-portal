# MP Portal — orientações de trabalho

## Escopo

Gerador do **site estático** da MP Soluções Corporativas: sete páginas
institucionais, o aviso de privacidade e um formulário de contato que envia a
solicitação por e-mail (`php/enviar.php`). O que é publicado é a pasta
`dist/site`, enviada ao `public_html` da hospedagem compartilhada da Hostinger
(`mp-solucoes.seg.br`). Não há banco, sessão, painel nem servidor de aplicação —
ADR 0006 (`docs/adr/0006-site-estatico-na-hospedagem-compartilhada.md`).

Fontes de verdade, nesta ordem: o código, este arquivo, o `README.md`,
`docs/operacao.md`, `docs/adr/`.

## Invariantes

- **Uma fonte para os metadados.** Título, descrição, imagem, rótulo de menu e
  linha do sitemap saem de `institucional/paginas.py`. Página nova = entrada
  nessa tabela + template. Há teste conferindo página a página.
- **O domínio não aparece em arquivo nenhum.** `canonical`, `og:url`, `robots`,
  `sitemap` e os endereços de e-mail saem do parâmetro `--dominio` do gerador
  (`DOMINIO` no Compose). Trocar de domínio é gerar de novo. Há teste que
  varre `institucional/`, `templates/`, `static/` e `php/`.
- **Segmentos e soluções do formulário têm uma tabela só**
  (`SEGMENTOS` e `SOLUCOES` em `paginas.py`): o gerador as injeta no
  `enviar.php`, e o HTML do formulário sai delas.
- **O formulário só é publicado com `COM_FORMULARIO=1`** (`--com-formulario`),
  porque depende de uma caixa de e-mail que receba. Sem ele, a página de contato
  oferece só telefone, WhatsApp e e-mail, e o `enviar.php` nem vai para a saída.
- **O `enviar.php` não grava a solicitação.** O que fica em disco é o resumo
  HMAC do endereço de rede, apagado em até uma hora. Qualquer campo novo ou
  dado novo guardado passa pelo aviso de privacidade
  (`templates/site/privacidade.html`): ele declara linha a linha o que é
  recebido; mude o texto e a versão juntos.
- **A configuração do formulário fica fora do `public_html`**
  (`../contato-config.php`, modelo em `php/contato-config.exemplo.php`), nunca
  no Git.
- **Recurso externo é exceção declarada, não proibição.** Por padrão, fontes e
  imagens de `static/site/` são vendorizadas, e há teste que reprova referência
  a host externo — é o que mantém a CSP fechada e o visitante longe de
  rastreamento de terceiros. Quando um recurso externo fizer sentido (vídeo,
  mapa, analytics), ele entra: ajuste a CSP e o teste na mesma mudança e
  registre o motivo — inclusive no aviso de privacidade.
- **CSP estrita**: `default-src 'self'`, de `sharedauth.security.montar_csp()`,
  gravada no `.htaccess` pelo gerador. A folga atual é `img-src data:`, pelo SVG
  de ruído do `site.css`; estilo e script ficam em arquivo, não embutidos.
- **URL limpa, uma página um documento.** `/solucoes` serve `solucoes.html`; a
  forma `/solucoes.html` responde 301 (já foi indexada). Está no `.htaccess`.
- **`{% static %}` é do projeto** (`institucional/tags_estaticas.py`): caminho na
  raiz, com `?v=` pelo conteúdo. Arquivo inexistente é erro de build.
- **LF, sem BOM**, em todo arquivo. `.gitattributes` força; há teste.
- **Acento em texto de interface, nunca em identificador.** Rótulo exibido,
  mensagem e documento levam acento; nome de campo, valor de formulário, chave
  de dicionário e nome de teste são ASCII.
- **Comentário de template em várias linhas é `{% comment %}`** — a forma
  `{# #}` só vale em uma linha. Há teste procurando sintaxe vazada.

## Suíte

```bash
docker compose run --build --rm quality
```

O `--build` **não é opcional**: sem ele a suíte roda sobre a imagem anterior.
Roda Ruff (`check` e `format --check`) e o pytest, que gera o site de verdade e
confere a saída.

O `enviar.php` é testado à parte, num contêiner `php:cli` (`php/testar.sh`; o
comando está no `README.md`). Mexeu no PHP: rode.

O que merece teste, em que camada e em que forma está em `docs/TESTES.md`,
comum aos repositórios; leia antes de escrever ou remover um teste.

Diante de vermelho, decida de quem é o defeito antes de mexer: teste que mede
texto literal reprova mudança legítima, e nesse caso quem se corrige é a
asserção. Nunca escreva código para o teste passar.

E rode no navegador antes de considerar pronto
(`python -m institucional.previa dist/site 5601`): defeitos de template e de
imagem já passaram pela suíte inteira e só apareceram abrindo a página.

## Dependências

Faixa no `pyproject.toml` (contrato de compatibilidade) e versão exata no
`uv.lock` (o que é testado). O Django entra só como motor de template, em tempo
de build. `sharedauth` vem por referência Git, fixada em tag, **sem o extra
`[flask]`**.

O lock se regenera em contêiner (não há `uv` no host):

```bash
docker run --rm -v "${PWD}:/w" -w /w python:3.14-slim \
  sh -c "apt-get update -qq && apt-get install -y -qq git && pip install -q uv==0.12.10 && uv lock"
```

(No Git Bash do Windows, prefixe com `MSYS_NO_PATHCONV=1` e use o caminho
absoluto no `-v`.)

## Conteúdo institucional

As sete páginas vieram, byte a byte, do repositório `MpSolucoes`, removido em
10/09/2026; o histórico dele está no bundle `mp-solucoes-f5-arquivo.bundle`, em
`Dropbox/Programacao/`.

Imagens novas entram como `webp` (qualidade ~82, largura máx. 1600), com
`width`/`height` declarados e `loading="lazy"` abaixo da dobra — sem isso a
página salta enquanto carrega, que é critério de Core Web Vitals.
