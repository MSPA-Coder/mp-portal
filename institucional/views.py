"""As paginas publicas do site, mais `robots.txt` e `sitemap.xml`.

Nenhuma delas consulta o banco, e isso importa: incorporar o site ao portal fez
o institucional passar a depender da aplicacao, e a unica coisa que reduz esse
custo e o conteudo publico continuar servivel enquanto o PostgreSQL nao
responde. Ha teste que reprova consulta ao banco nestas rotas.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from institucional.paginas import PAGINAS, Pagina


def contexto_da_pagina(pagina: Pagina) -> dict:
    """O que o `<head>` e o menu precisam saber sobre esta pagina."""
    return {
        "titulo": pagina.titulo,
        "descricao": pagina.descricao,
        "classe_do_corpo": pagina.classe_do_corpo,
        "imagem": pagina.imagem,
        "imagem_alt": pagina.imagem_alt,
        "pagina_ativa": pagina.nome,
    }


def montar_view(pagina: Pagina) -> Callable[[HttpRequest], HttpResponse]:
    """Fabrica a view de uma pagina institucional.

    Uma funcao por pagina, e nao uma view generica com parametro na URL: rota
    generica aceitaria qualquer coisa e devolveria 404 la dentro, e o mapa de
    URLs deixaria de dizer quais paginas existem.
    """

    def view(request: HttpRequest) -> HttpResponse:
        return render(request, pagina.template, contexto_da_pagina(pagina))

    view.__name__ = f"pagina_{pagina.nome}"
    return view


def robots(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "site/robots.txt",
        {"url_base": request.build_absolute_uri("/").rstrip("/")},
        content_type="text/plain; charset=utf-8",
    )


def sitemap(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "site/sitemap.xml",
        {
            "url_base": request.build_absolute_uri("/").rstrip("/"),
            "paginas": PAGINAS,
        },
        content_type="application/xml; charset=utf-8",
    )
