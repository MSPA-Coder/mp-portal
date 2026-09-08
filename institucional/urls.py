"""Rotas publicas do site institucional.

A pagina `/contato` NAO esta aqui: ela responde GET e POST, e quem a serve e
`contatos.views.contato`, porque o POST grava. As outras seis sao leitura pura.

As formas com `.html` respondem 301 para a URL limpa. Elas existiam quando o
site era estatico, e sumir com elas depois de indexadas custaria posicao no
buscador.
"""

from django.urls import path
from django.views.generic import RedirectView

from institucional import views
from institucional.paginas import PAGINAS

urlpatterns = [
    path(pagina.rota, views.montar_view(pagina), name=f"pagina_{pagina.nome}")
    for pagina in PAGINAS
    if pagina.nome != "contato"
]

urlpatterns += [
    path(
        f"{pagina.rota}.html",
        RedirectView.as_view(url=pagina.caminho, permanent=True),
    )
    for pagina in PAGINAS
    if pagina.rota
]

urlpatterns += [
    path("index.html", RedirectView.as_view(url="/", permanent=True)),
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
]
