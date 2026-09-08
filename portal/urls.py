"""Mapa de URLs do MP Portal."""

from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import include, path
from django.views.decorators.http import require_POST
from django.views.generic import RedirectView

from core.views import health_check


@require_POST
def sair(request):
    """Encerra a sessao. Somente POST, para nao ser acionavel por link ou imagem."""
    logout(request)
    return redirect("login")


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login", permanent=False)),
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
    path("", include("contatos.urls")),
]
