"""Contexto compartilhado pelas telas que usam a casca do site.

O menu institucional aparece nas sete paginas publicas e na tela de login, e
todas saem da mesma tabela (`institucional/paginas.py`). Um processador de
contexto entrega essa lista sem que cada view precise lembrar de passa-la.

A area logada tem casca propria desde a ADR 0005 e nao consome `paginas` -- o
processador roda para toda resposta, mas ali a variavel so fica sem uso.
"""

from __future__ import annotations

from django.http import HttpRequest

from institucional.paginas import PAGINAS


def navegacao(_request: HttpRequest) -> dict:
    return {"paginas": PAGINAS}
