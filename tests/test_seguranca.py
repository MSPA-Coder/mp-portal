"""Cabecalhos, politica e superficie: o que vale para toda resposta."""

from __future__ import annotations

import pytest
from django.conf import settings
from sharedauth.security import SECURITY_HEADERS, montar_csp

from core.security import CONTENT_SECURITY_POLICY
from institucional.paginas import PAGINAS

pytestmark = pytest.mark.django_db


def test_politica_e_a_fechada_da_biblioteca_compartilhada():
    """Abrir uma diretiva exige mudar aqui tambem, e explicar por que."""
    assert montar_csp(imagens_data_uri=True) == CONTENT_SECURITY_POLICY
    assert "unsafe-inline" not in CONTENT_SECURITY_POLICY
    assert CONTENT_SECURITY_POLICY.startswith("default-src 'self'")


def test_toda_resposta_carrega_a_politica_e_os_defensivos(client):
    for caminho in ("/", "/contato", "/privacidade", "/login", "/health"):
        resposta = client.get(caminho)
        assert resposta["Content-Security-Policy"] == CONTENT_SECURITY_POLICY, caminho
        for cabecalho, valor in SECURITY_HEADERS.items():
            assert resposta[cabecalho] == valor, f"{caminho}: {cabecalho}"


def test_nenhuma_pagina_vaza_sintaxe_de_template(client, atendente):
    """Comentario `{# #}` escrito em varias linhas NAO e comentario.

    A forma com cerquilha so vale numa linha; em duas, o texto sai no HTML. Foi
    o que aconteceu no `base.html`, dentro do `<head>`, e nenhuma asercao de
    conteudo percebeu -- todas procuravam o que DEVIA estar la. Esta procura o
    que NAO devia.
    """
    from django.utils import timezone

    from contatos.models import Contato
    from contatos.privacidade import AVISO_VERSAO

    contato = Contato.objects.create(
        nome="Fulano",
        email="fulano@exemplo.com.br",
        telefone="11999998888",
        consentimento=True,
        consentimento_em=timezone.now(),
        aviso_versao=AVISO_VERSAO,
    )

    caminhos = [c.caminho for c in PAGINAS] + ["/login", "/privacidade", "/contato/recebido"]
    for caminho in caminhos:
        corpo = client.get(caminho).content.decode("utf-8")
        for marca in ("{#", "{%", "{{"):
            assert marca not in corpo, f"{caminho} vazou {marca}"

    client.force_login(atendente)
    for caminho in ("/painel/atendimento/", f"/painel/atendimento/{contato.pk}/"):
        corpo = client.get(caminho).content.decode("utf-8")
        for marca in ("{#", "{%", "{{"):
            assert marca not in corpo, f"{caminho} vazou {marca}"


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


def test_a_raiz_e_o_site_institucional(client):
    """Antes da incorporacao a raiz desviava para o login. Agora o portal E o site."""
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "MP SOLUÇÕES CORPORATIVAS" in resposta.content.decode("utf-8")


def test_data_uri_so_esta_liberado_para_imagem(client):
    """A folga existe por UMA razao escrita: o SVG de ruido dentro do site.css."""
    assert "img-src 'self' data:" in CONTENT_SECURITY_POLICY
    assert "script-src 'self';" in CONTENT_SECURITY_POLICY
    assert "style-src 'self';" in CONTENT_SECURITY_POLICY
    assert "font-src 'self'" in CONTENT_SECURITY_POLICY
    assert CONTENT_SECURITY_POLICY.count("data:") == 1


def test_logout_nao_acontece_por_get(client, atendente):
    """Link ou imagem apontando para /logout derrubaria a sessao de quem abrisse."""
    client.force_login(atendente)

    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
