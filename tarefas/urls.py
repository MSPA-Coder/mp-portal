"""Rotas do app `tarefas`, todas sob `/tarefas/` e todas sob sessao.

Nenhuma rota publica aqui -- diferente de `contatos`, que serve a pagina de
contato do site alem da area interna. Por isso o prefixo unico: um caminho que
comeca com `/tarefas/` esta atras de `somente_equipe`, sem excecao a conferir.
"""

from django.urls import path

from tarefas import views

urlpatterns = [
    path("tarefas/", views.lista, name="tarefas_lista"),
    path("tarefas/nova", views.nova, name="tarefa_nova"),
    path("tarefas/<int:pk>/", views.detalhe, name="tarefa_detalhe"),
    path("tarefas/<int:pk>/editar", views.editar, name="tarefa_editar"),
    path("tarefas/<int:pk>/situacao", views.mudar_situacao, name="tarefa_situacao"),
    path(
        "tarefas/<int:pk>/andamento",
        views.registrar_andamento,
        name="tarefa_andamento",
    ),
]
