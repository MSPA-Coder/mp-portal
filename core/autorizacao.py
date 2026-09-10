"""Quem pode abrir as telas de administracao do portal.

Uma regra so: **conta que administra**, marcada por `is_staff`. Hoje ela
guarda o atendimento -- os pedidos que chegam pelo formulario publico, com dado
pessoal de terceiro que a ADR 0005 decidiu NAO abrir para o circulo inteiro
antes de existir um sistema de perfis. Vale tambem para o CRUD de contas,
quando ele entrar.

As tarefas NAO usam mais este decorador -- desde a ADR 0005 elas sao
`login_required`, o espaco compartilhado das quatro pessoas. `is_staff` deixou
de significar "equipe da MP x cliente" e passou a significar "administra x usa".

O decorador continua aqui, e nao dentro de `contatos/views.py`, porque contas
vai reusa-lo: duas copias da mesma decisao de autorizacao divergem no dia em
que uma delas for corrigida.
"""

from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def somente_equipe(view):
    """Exige sessao e `is_staff`.

    Anonimo vai para o login; autenticado sem permissao recebe 403. A diferenca
    e proposital: mandar quem ja esta logado de volta ao login sugere que a
    sessao caiu, e a pessoa tenta de novo para sempre.
    """

    @wraps(view)
    def envolvida(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return envolvida
