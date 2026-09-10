"""Quem pode abrir as telas internas.

Existe uma regra so, e ela vale para as duas areas autenticadas de hoje --
atendimento e tarefas: **conta da equipe**, marcada por `is_staff`. Estava
escrita dentro de `contatos/views.py` enquanto havia uma area unica; subiu para
ca quando a segunda apareceu, porque duas copias da mesma decisao de
autorizacao divergem no dia em que uma delas for corrigida.

`is_staff` e nao "autenticado" e deliberado. O ADR 0002 registra que a area do
cliente vai existir, e a conta de cliente sera autenticada tambem -- se o
criterio fosse a sessao, o dia em que o primeiro cliente entrar seria o dia em
que ele passaria a ler as tarefas internas da MP.
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
