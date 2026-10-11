"""A tag `{% static %}` do gerador: caminho absoluto na raiz, com versao.

Substitui a do Django (o gerador nao tem `STATIC_ROOT` nem manifesto). O caminho
sai como `/site/css/site.css?v=ab12cd34`, e a versao e o inicio do SHA-256 do
arquivo: o `.htaccess` pode mandar o navegador guardar CSS, JS e fontes por um
ano, e ainda assim uma mudanca no arquivo chega ao visitante no mesmo deploy.

Arquivo inexistente e erro de build, e nao link quebrado em producao.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from django import template

register = template.Library()

#: Raiz dos arquivos estaticos do projeto. O gerador copia esta arvore para a
#: raiz do site, entao `static/site/css/site.css` vira `/site/css/site.css`.
RAIZ_ESTATICA = Path(__file__).resolve().parent.parent / "static"


def versao_do_arquivo(caminho: str) -> str:
    arquivo = RAIZ_ESTATICA / caminho
    if not arquivo.is_file():
        raise template.TemplateSyntaxError(f"static: arquivo inexistente: {caminho}")
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()[:8]


@register.simple_tag
def static(caminho: str) -> str:
    return f"/{caminho}?v={versao_do_arquivo(caminho)}"
