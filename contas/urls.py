"""Rotas do CRUD de contas, sob `/painel/contas/` e restritas a `is_staff`.

Todas atras de `somente_equipe` (ver `core/autorizacao.py`): a lista mostra
quem tem acesso ao portal, e criar conta e a acao mais sensivel que existe
aqui. O prefixo `/painel/` e a fronteira da ADR 0005; o `is_staff` e a segunda
tranca, na view.
"""

from django.urls import path

from contas import views

urlpatterns = [
    path("painel/contas/", views.contas_lista, name="contas_lista"),
    path("painel/contas/nova", views.conta_nova, name="conta_nova"),
    path("painel/contas/<int:pk>/", views.conta_editar, name="conta_editar"),
]
