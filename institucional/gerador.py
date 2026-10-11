"""Gerador do site estatico: renderiza os templates e monta a pasta publicavel.

    python -m institucional.gerador --dominio exemplo.com.br --saida dist

A saida e o que vai para o `public_html` da hospedagem: as paginas em `.html`,
`robots.txt`, `sitemap.xml`, `.htaccess`, os arquivos de `static/` e o
`enviar.php`. Nada aqui roda no servidor -- o Django serve so de motor de
template, em tempo de build.

O DOMINIO e parametro obrigatorio e nao esta escrito em arquivo nenhum do
repositorio: dele saem `canonical`, `og:url`, o sitemap e os enderecos de
e-mail. Trocar de dominio e gerar de novo.

`--com-formulario` liga o formulario da pagina de contato. Sem ele a pagina
mostra so telefone, WhatsApp e e-mail: o formulario depende de uma caixa de
e-mail que receba as solicitacoes, e publica-lo sem ela perderia contatos.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.template import Context, Engine
from sharedauth.security import SECURITY_HEADERS, montar_csp

from institucional import paginas as p

RAIZ = Path(__file__).resolve().parent.parent
MARCADOR_DO_ERRO = "<!--MENSAGEM-->"
_DOMINIO = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")

#: `img-src` abre para `data:` por causa do SVG de ruido do `site.css`. A
#: justificativa e a mesma que a biblioteca exige no ponto da chamada.
CSP = montar_csp(imagens_data_uri=True)


def _motor() -> Engine:
    if not settings.configured:
        settings.configure(DEFAULT_CHARSET="utf-8", USE_TZ=False)
    return Engine(
        dirs=[str(RAIZ / "templates")],
        libraries={"static": "institucional.tags_estaticas"},
        builtins=[],
        autoescape=True,
    )


def contexto_base(dominio: str, *, com_formulario: bool) -> dict:
    return {
        "url_base": f"https://{dominio}",
        "paginas": list(p.PAGINAS),
        "com_formulario": com_formulario,
        "telefone": p.TELEFONE,
        "whatsapp": p.WHATSAPP,
        "whatsapp_link": p.WHATSAPP_LINK,
        "email": f"{p.CAIXA_PUBLICA}@{dominio}",
        "segmentos": p.SEGMENTOS,
        "solucoes": p.SOLUCOES,
    }


def renderizar_pagina(motor: Engine, pagina: p.Pagina, base: dict) -> str:
    contexto = {
        **base,
        "titulo": pagina.titulo,
        "descricao": pagina.descricao,
        "classe_do_corpo": pagina.classe_do_corpo,
        "imagem": pagina.imagem,
        "imagem_alt": pagina.imagem_alt,
        "pagina_ativa": pagina.nome,
        "caminho": pagina.caminho,
        "indexavel": pagina.indexavel,
        "marcador_do_erro": MARCADOR_DO_ERRO,
    }
    return motor.get_template(pagina.template).render(Context(contexto))


def robots(dominio: str) -> str:
    return (
        "# Todo o conteudo e publico. A confirmacao e o molde de erro do formulario\n"
        "# nao tem o que indexar.\n\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /contato-enviado\n"
        "Disallow: /contato-erro\n\n"
        f"Sitemap: https://{dominio}/sitemap.xml\n"
    )


def sitemap(dominio: str) -> str:
    linhas = [
        f"  <url><loc>https://{dominio}{pg.caminho}</loc></url>"
        for pg in (*p.PAGINAS, *p.PAGINAS_DE_APOIO)
        if pg.indexavel
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(linhas)
        + "\n</urlset>\n"
    )


def htaccess() -> str:
    """Regras do servidor: HTTPS, URL limpa, 301 de `.html`, cabecalhos e cache.

    Os cabecalhos e a CSP vem de `sharedauth.security`, a mesma fonte dos
    outros aplicativos. `Header always set` cobre tambem as respostas de erro.
    """
    cabecalhos = {**SECURITY_HEADERS, "Content-Security-Policy": CSP}
    linhas_cabecalho = "\n".join(
        f'  Header always set {nome} "{valor}"' for nome, valor in cabecalhos.items()
    )
    return f"""# Gerado por institucional/gerador.py -- nao edite no servidor.

DirectoryIndex index.html
Options -Indexes -MultiViews

<IfModule mod_rewrite.c>
  RewriteEngine On

  # HTTPS sempre. A Hostinger termina o TLS no proxy e informa o esquema.
  RewriteCond %{{HTTPS}} !=on
  RewriteCond %{{HTTP:X-Forwarded-Proto}} !https
  RewriteRule ^ https://%{{HTTP_HOST}}%{{REQUEST_URI}} [L,R=301]

  # `/solucoes.html` e `/index.html` ja foram indexados: 301 para a URL limpa.
  # O teste em THE_REQUEST impede o laco com a reescrita interna abaixo.
  RewriteCond %{{THE_REQUEST}} \\s/+index\\.html[\\s?] [NC]
  RewriteRule ^index\\.html$ / [R=301,L]
  RewriteCond %{{THE_REQUEST}} \\s/+([^\\s?]+)\\.html[\\s?] [NC]
  RewriteRule ^(.+)\\.html$ /$1 [R=301,L]

  # URL limpa: `/solucoes` serve `solucoes.html`.
  RewriteCond %{{REQUEST_FILENAME}} !-d
  RewriteCond %{{REQUEST_FILENAME}}.html -f
  RewriteRule ^(.+)$ $1.html [L]
</IfModule>

<IfModule mod_headers.c>
{linhas_cabecalho}
  Header always set Strict-Transport-Security "max-age=31536000"
</IfModule>

ErrorDocument 404 /404.html

<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresDefault "access plus 1 hour"
  ExpiresByType text/html "access plus 0 seconds"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType application/javascript "access plus 1 year"
  ExpiresByType text/javascript "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
  ExpiresByType image/webp "access plus 1 month"
  ExpiresByType image/svg+xml "access plus 1 month"
</IfModule>

# O PHP so atende o formulario. Qualquer outro .php e recusado.
<FilesMatch "^(?!enviar\\.php$).+\\.php$">
  Require all denied
</FilesMatch>
"""


def _literal_php(pares: tuple[tuple[str, str], ...]) -> str:
    def aspas(texto: str) -> str:
        return "'" + texto.replace("\\", "\\\\").replace("'", "\\'") + "'"

    return "[" + ", ".join(f"{aspas(k)} => {aspas(v)}" for k, v in pares) + "]"


def enviar_php() -> str:
    """O `enviar.php` com as listas de segmento e solucao da tabela unica."""
    texto = (RAIZ / "php" / "enviar.php").read_text(encoding="utf-8")
    for marcador, pares in (
        ("/*@@SEGMENTOS@@*/ []", p.SEGMENTOS),
        ("/*@@SOLUCOES@@*/ []", p.SOLUCOES),
    ):
        if texto.count(marcador) != 1:
            raise SystemExit(f"enviar.php: marcador ausente: {marcador}")
        texto = texto.replace(marcador, _literal_php(pares))
    return texto


def gerar(destino: Path, dominio: str, *, com_formulario: bool = False) -> list[Path]:
    """Monta `destino` do zero e devolve os arquivos gravados."""
    if not _DOMINIO.match(dominio):
        raise SystemExit(f"dominio invalido: {dominio!r}")
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    motor = _motor()
    base = contexto_base(dominio, com_formulario=com_formulario)
    gravados: list[Path] = []

    def gravar(nome: str, texto: str) -> None:
        caminho = destino / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        gravados.append(caminho)

    for pagina in (*p.PAGINAS, *p.PAGINAS_DE_APOIO):
        gravar(pagina.arquivo, renderizar_pagina(motor, pagina, base))
    gravar("404.html", motor.get_template("site/404.html").render(Context(base)))
    gravar("robots.txt", robots(dominio))
    gravar("sitemap.xml", sitemap(dominio))
    gravar(".htaccess", htaccess())

    # A arvore de `static/` vira a raiz do site.
    for origem in sorted((RAIZ / "static").rglob("*")):
        if origem.is_file():
            alvo = destino / origem.relative_to(RAIZ / "static")
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origem, alvo)
            gravados.append(alvo)

    if com_formulario:
        gravar("enviar.php", enviar_php())
    return gravados


def principal(argv: list[str] | None = None) -> None:
    analisador = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    # As variaveis existem para o Compose (`docker compose run -e ...`); na linha
    # de comando, o argumento vale mais que o ambiente.
    analisador.add_argument(
        "--dominio", default=os.environ.get("DOMINIO"), help="ex.: exemplo.com.br"
    )
    analisador.add_argument("--saida", default="dist", type=Path)
    analisador.add_argument(
        "--com-formulario",
        action="store_true",
        default=os.environ.get("COM_FORMULARIO", "0") in {"1", "true"},
    )
    args = analisador.parse_args(argv)
    if not args.dominio:
        analisador.error("informe --dominio (ou a variavel DOMINIO)")
    arquivos = gerar(args.saida, args.dominio, com_formulario=args.com_formulario)
    print(f"{len(arquivos)} arquivos em {args.saida}")


if __name__ == "__main__":
    principal()
