"""Cabecalhos, politica e superficie: o que vale para toda resposta."""

from __future__ import annotations

import pytest
from django.conf import settings
from sharedauth.security import SECURITY_HEADERS, montar_csp

from core.security import CONTENT_SECURITY_POLICY

pytestmark = pytest.mark.django_db


def test_politica_e_a_fechada_da_biblioteca_compartilhada():
    """Abrir uma diretiva exige mudar aqui tambem, e explicar por que."""
    assert montar_csp() == CONTENT_SECURITY_POLICY
    assert "unsafe-inline" not in CONTENT_SECURITY_POLICY
    assert CONTENT_SECURITY_POLICY.startswith("default-src 'self'")


def test_toda_resposta_carrega_a_politica_e_os_defensivos(client):
    for caminho in ("/privacidade", "/login", "/health"):
        resposta = client.get(caminho)
        assert resposta["Content-Security-Policy"] == CONTENT_SECURITY_POLICY, caminho
        for cabecalho, valor in SECURITY_HEADERS.items():
            assert resposta[cabecalho] == valor, f"{caminho}: {cabecalho}"


def test_settings_do_django_nao_discordam_da_biblioteca():
    """Dois lugares emitem os mesmos cabecalhos; divergir e defeito silencioso."""
    assert SECURITY_HEADERS["X-Frame-Options"] == settings.X_FRAME_OPTIONS
    assert SECURITY_HEADERS["Referrer-Policy"] == settings.SECURE_REFERRER_POLICY
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True


def test_admin_do_django_nao_esta_instalado(client):
    """Ele registraria o modelo de usuario e abriria um segundo login."""
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    assert client.get("/admin/").status_code == 404


def test_depuracao_desligada_por_padrao():
    assert settings.DEBUG is False


def test_cookie_de_sessao_e_fechado():
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_HTTPONLY is True


def test_a_raiz_leva_ao_login(client):
    resposta = client.get("/")

    assert resposta.status_code == 302
    assert resposta["Location"] == "/login"


def test_logout_nao_acontece_por_get(client, atendente):
    """Link ou imagem apontando para /logout derrubaria a sessao de quem abrisse."""
    client.force_login(atendente)

    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
