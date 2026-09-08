"""Fixtures da suite.

TODA ESTA SUITE TOCA O BANCO, e isso e resposta direta ao achado L01 do
LEVANTAMENTO_2026-09.md: os aplicativos da frota somavam centenas de testes e
nenhum abria uma conexao, entao restricao de banco, migracao e transacao eram
verificadas por leitura. Aqui as `CheckConstraint` sao exercitadas contra o
PostgreSQL de verdade, e cada execucao aplica a cadeia inteira de migracoes a
um banco vazio -- porque e assim que o `pytest-django` constroi o banco de
teste. Uma migracao que falha ao executar reprova na CI, e nao no `deploy.sh`,
que reverte codigo e imagem mas nao reverte migracao.

O banco e o servico `postgres-teste` do Compose: efemero, em tmpfs, e
deliberadamente NAO e o `postgres` com dados reais.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

ORIGEM_DO_SITE = "https://site.exemplo"
ORIGEM_ESTRANHA = "https://outro.exemplo"

SENHA_DE_TESTE = "senha-de-teste-longa-2026"


@pytest.fixture
def client_com_csrf() -> Client:
    # O cliente de teste do Django dispensa CSRF por padrao; religar e o que
    # torna o teste de CSRF nao decorativo.
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def origens(settings):
    """Deixa a rota de contato aceitar a origem do site fabricada aqui."""
    settings.CONTATO_ORIGENS_PERMITIDAS = (ORIGEM_DO_SITE,)
    return settings


@pytest.fixture
def envio_valido() -> dict[str, object]:
    return {
        "nome": "Maria Souza",
        "empresa": "Condominio Alfa",
        "email": "maria@exemplo.com.br",
        "telefone": "(11) 98888-7777",
        "segmento": "condominios",
        "solucoes": ["portaria", "facilities"],
        "mensagem": "Precisamos avaliar portaria remota para 2 torres.",
        "consentimento": "on",
    }


@pytest.fixture
def atendente(db):
    return get_user_model().objects.create_user(
        username="atendente",
        password=SENHA_DE_TESTE,
        is_staff=True,
    )


@pytest.fixture
def pessoa_sem_acesso(db):
    return get_user_model().objects.create_user(
        username="visitante",
        password=SENHA_DE_TESTE,
        is_staff=False,
    )
