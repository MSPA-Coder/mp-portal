"""Rotas do app `tarefas`, todas sob `/painel/tarefas/` e todas sob sessao.

Nenhuma rota publica aqui. O prefixo `/painel/` e a fronteira estrutural da
ADR 0005: um caminho que comeca com `/painel/` esta atras de sessao, e a
garantia e uma regra so em vez de vigilancia por app. Os enderecos antigos
(`/tarefas/...`) respondem 301 para os novos, em `portal/urls.py`.

Os `name=` nao mudaram: `reverse()` e `{% url %}` continuam funcionando, e por
isso nem as views nem os templates precisaram ser tocados na mudanca de prefixo.
"""

from django.urls import path

from tarefas import views

urlpatterns = [
    path("painel/tarefas/", views.lista, name="tarefas_lista"),
    path("painel/tarefas/nova", views.nova, name="tarefa_nova"),
    path("painel/tarefas/<int:pk>/", views.detalhe, name="tarefa_detalhe"),
    path("painel/tarefas/<int:pk>/editar", views.editar, name="tarefa_editar"),
    path("painel/tarefas/<int:pk>/situacao", views.mudar_situacao, name="tarefa_situacao"),
    path(
        "painel/tarefas/<int:pk>/andamento",
        views.registrar_andamento,
        name="tarefa_andamento",
    ),
]
