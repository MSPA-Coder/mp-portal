"""Rotas do app `contatos`: as publicas na raiz, a leitura interna sob `/painel/`.

`/contato` (singular) e a pagina PUBLICA, que responde GET e POST na mesma
rota; `/painel/atendimento/` (sob sessao) e a leitura interna. Nomes parecidos
com publicos opostos sao um convite a engano, entao a distincao esta no caminho
e nao so na autorizacao -- e agora tambem no prefixo: tudo que e interno mora
sob `/painel/` (ADR 0005). Os enderecos antigos (`/atendimento/...`) respondem
301 para os novos, em `portal/urls.py`.
"""

from django.urls import path

from contatos import views

urlpatterns = [
    path("contato", views.contato, name="contato"),
    path("contato/recebido", views.recebido, name="contato_recebido"),
    path("privacidade", views.privacidade, name="privacidade"),
    path("painel/atendimento/", views.atendimento_lista, name="atendimento_lista"),
    path(
        "painel/atendimento/<int:pk>/",
        views.atendimento_detalhe,
        name="atendimento_detalhe",
    ),
    path(
        "painel/atendimento/<int:pk>/situacao",
        views.atendimento_situacao,
        name="atendimento_situacao",
    ),
    path(
        "painel/atendimento/<int:pk>/excluir",
        views.atendimento_excluir,
        name="atendimento_excluir",
    ),
]
