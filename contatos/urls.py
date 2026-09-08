"""Rotas do app `contatos`.

`/contato` (singular) e a pagina PUBLICA, que responde GET e POST na mesma
rota; `/atendimento/` (sob sessao) e a leitura interna. Nomes parecidos com
publicos opostos sao um convite a engano, entao a distincao esta no caminho e
nao so na autorizacao -- e o teste de autorizacao cobre as duas familias
separadamente.
"""

from django.urls import path

from contatos import views

urlpatterns = [
    path("contato", views.contato, name="contato"),
    path("contato/recebido", views.recebido, name="contato_recebido"),
    path("privacidade", views.privacidade, name="privacidade"),
    path("atendimento/", views.atendimento_lista, name="atendimento_lista"),
    path("atendimento/<int:pk>/", views.atendimento_detalhe, name="atendimento_detalhe"),
    path(
        "atendimento/<int:pk>/situacao",
        views.atendimento_situacao,
        name="atendimento_situacao",
    ),
    path(
        "atendimento/<int:pk>/excluir",
        views.atendimento_excluir,
        name="atendimento_excluir",
    ),
]
