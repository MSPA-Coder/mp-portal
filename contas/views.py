"""Para onde cada conta vai depois de entrar.

DESTINO DERIVADO, e nao fixo. Hoje existe uma area autenticada so -- o
atendimento, da equipe da MP. A decisao registrada e que havera duas, em areas
separadas: equipe e cliente (ver
`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`). Esta view e a
emenda por onde a segunda entra: no dia em que `/cliente/` existir, muda-se uma
funcao e nenhuma navegacao precisa ser reescrita.

O padrao vem do ControleBancario, que manda cada pessoa para a primeira tela a
que ela tem acesso em vez de para um endereco fixo -- e o motivo la vale aqui:
destino fixo obriga a tela de destino a nao exigir permissao nenhuma.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse


@login_required
def apos_login(request: HttpRequest) -> HttpResponse:
    """Encaminha para a area da conta que entrou."""
    if request.user.is_staff:
        return HttpResponseRedirect(reverse("atendimento_lista"))
    # Conta sem area propria ainda: volta ao site, autenticada. Quando a area
    # do cliente existir, o destino dela entra aqui -- e nao num `if` espalhado
    # por templates.
    return HttpResponseRedirect("/")
