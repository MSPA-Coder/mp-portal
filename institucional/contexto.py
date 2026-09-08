"""Contexto compartilhado por toda resposta HTML.

O menu precisa existir na tela de login e na area de atendimento tanto quanto
nas paginas institucionais -- e uma casca so foi o motivo de incorporar o site
ao portal. Um processador de contexto entrega a lista de paginas a todas as
views sem que cada uma precise lembrar de passa-la.
"""

from __future__ import annotations

from django.http import HttpRequest

from institucional.paginas import PAGINAS


def navegacao(_request: HttpRequest) -> dict:
    return {"paginas": PAGINAS}
