"""A sonda que o Compose, o `deploy.sh` e o vigia do VPS consultam."""

from __future__ import annotations

from unittest import mock

import pytest


@pytest.mark.django_db
def test_health_responde_ok_consultando_o_banco(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"servico": "mp-portal", "status": "ok"}


@pytest.mark.django_db
def test_health_atende_com_e_sem_barra(client):
    """Vigia externo que nao segue redirecionamento marcaria 301 como queda."""
    assert client.get("/health").status_code == 200
    assert client.get("/health/").status_code == 200


def test_health_devolve_503_quando_o_banco_nao_responde(client):
    """503 e nao 500: indisponibilidade temporaria, sem traceback a cada sonda."""
    with mock.patch("core.views.connection") as conexao:
        conexao.cursor.side_effect = RuntimeError("banco inalcancavel")
        resposta = client.get("/health")

    assert resposta.status_code == 503
    assert resposta.json() == {"servico": "mp-portal", "status": "erro"}
