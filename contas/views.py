"""Para onde cada conta vai depois de entrar.

DESTINO DERIVADO, e nao fixo. Hoje todas as contas do circulo vao para o mesmo
lugar -- as tarefas, o espaco compartilhado da ADR 0005. A decisao registrada e
que havera uma area de cliente externo separada (ver
`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`); esta view e a emenda
por onde ela entra: no dia em que `/painel/cliente/` existir, muda-se esta
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
    """Encaminha para a area da conta que entrou.

    Um destino so por enquanto: as tarefas. Quando a area do cliente externo
    existir, a ramificacao por conta entra aqui -- e nao num `if` espalhado por
    templates.
    """
    return HttpResponseRedirect(reverse("tarefas_lista"))
