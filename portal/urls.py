"""Mapa de URLs do MP Portal.

A raiz e o site institucional, e nao mais um desvio para o login: depois da
incorporacao, o portal E o site. As rotas autenticadas ficam todas sob
`/painel/` (ADR 0005 -- um prefixo so em vez de vigilancia por app), e o login
e `/login` -- nome escolhido porque o nginx central do VPS aplica limite de
taxa exatamente a `POST /login`, e por isso ele NAO se move para `/painel/`.

Os enderecos anteriores a ADR 0005 (`/tarefas/...`, `/atendimento/...`)
respondem 301 para os equivalentes sob `/painel/` -- `_legado_para_painel()`.
"""

from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import include, path
from django.views.decorators.http import require_POST
from django.views.generic import RedirectView

from contas.views import apos_login
from core.views import health_check


@require_POST
def sair(request):
    """Encerra a sessao. Somente POST, para nao ser acionavel por link ou imagem."""
    logout(request)
    return redirect("/")


def _legado_para_painel(prefixo: str) -> list:
    """301 dos enderecos pre-ADR-0005 (`/<prefixo>/...`) para `/painel/<prefixo>/...`.

    Sao telas atras de login, sem link externo -- o que se protege aqui e o
    marcador de pagina de quem ja usava. `query_string=True` preserva o
    `?situacao=` da lista.
    """
    return [
        path(
            f"{prefixo}/<path:resto>",
            RedirectView.as_view(
                url=f"/painel/{prefixo}/%(resto)s", permanent=True, query_string=True
            ),
        ),
        path(
            f"{prefixo}/",
            RedirectView.as_view(
                url=f"/painel/{prefixo}/", permanent=True, query_string=True
            ),
        ),
    ]


urlpatterns = [
    path("health/", health_check, name="health_check"),
    # Sem barra tambem: os aplicativos Flask da frota servem `/health`, e o
    # `APPEND_SLASH` do Django responderia 301 ao caminho sem barra. Vigia
    # externo que nao segue redirecionamento marcaria o servico como fora do
    # ar. Sem `name=`: a rota canonica para `reverse()` continua sendo uma so.
    path("health", health_check),
    path(
        "login",
        LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("login/", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("logout", sair, name="logout"),
    path("apos-login", apos_login, name="apos_login"),
    # 301 dos enderecos internos anteriores a ADR 0005. Antes dos `include`
    # porque `contatos.urls`/`tarefas.urls` ja nao registram estes prefixos.
    *_legado_para_painel("tarefas"),
    *_legado_para_painel("atendimento"),
    # As rotas do site institucional e as do painel compartilham a raiz.
    # `contatos` vem antes porque serve `/contato`, que o institucional
    # deliberadamente nao registra (aquela pagina responde GET e POST).
    path("", include("contatos.urls")),
    path("", include("tarefas.urls")),
    path("", include("institucional.urls")),
]
