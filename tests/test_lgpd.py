"""O que torna o aviso de privacidade verificavel em vez de decorativo.

Tres perguntas, e as tres tem resposta mecanica aqui:

1. o aviso descreve exatamente o que o sistema guarda?
2. o prazo prometido e realmente aplicado?
3. uma implantacao publica sem canal para o titular consegue subir?
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from contatos import privacidade as aviso
from contatos.checks import (
    CANAL_AUSENTE,
    RETENCAO_INVALIDA,
    verificar_configuracao_publica,
)
from contatos.models import Contato, Situacao

pytestmark = pytest.mark.django_db


def criar_contato(**ajustes) -> Contato:
    dados = {
        "nome": "Fulano",
        "email": "fulano@exemplo.com.br",
        "telefone": "11999998888",
        "consentimento": True,
        "consentimento_em": timezone.now(),
        "aviso_versao": aviso.AVISO_VERSAO,
    }
    dados.update(ajustes)
    return Contato.objects.create(**dados)


def envelhecer(contato: Contato, dias: int) -> None:
    """`criado_em` e `auto_now_add`: so um UPDATE direto muda a data."""
    Contato.objects.filter(pk=contato.pk).update(
        criado_em=timezone.now() - timedelta(days=dias)
    )


# ---------------------------------------------------------------------------
# 1. O aviso descreve o que o sistema guarda
# ---------------------------------------------------------------------------


def test_aviso_declara_exatamente_os_campos_do_modelo():
    """Campo novo sem linha no aviso reprova aqui, e nao depois de coletar."""
    do_modelo = {
        campo.name for campo in Contato._meta.get_fields() if campo.name != "id"
    }

    assert set(aviso.CAMPOS_DECLARADOS) == do_modelo


def test_todo_campo_declarado_tem_rotulo_para_exibicao():
    assert set(aviso.ROTULOS_DE_CAMPO) == set(aviso.CAMPOS_DECLARADOS)


def test_pagina_do_aviso_e_publica_e_mostra_versao_e_prazo(client, settings):
    settings.CONTATO_CANAL_TITULAR = "privacidade@exemplo.com.br"

    resposta = client.get("/privacidade")
    corpo = resposta.content.decode("utf-8")

    assert resposta.status_code == 200
    assert aviso.AVISO_VERSAO in corpo
    assert str(settings.CONTATO_RETENCAO_DIAS) in corpo
    assert "privacidade@exemplo.com.br" in corpo
    # O rotulo, e nao o nome da coluna do banco.
    assert aviso.ROTULOS_DE_CAMPO["ip_hash"] in corpo


def test_pagina_do_aviso_avisa_quando_o_canal_nao_esta_configurado(client, settings):
    settings.CONTATO_CANAL_TITULAR = ""

    corpo = client.get("/privacidade").content.decode("utf-8")

    assert "ainda não configurado" in corpo


# ---------------------------------------------------------------------------
# 2. O prazo prometido e aplicado
# ---------------------------------------------------------------------------


def test_expurgo_apaga_o_que_passou_do_prazo(settings):
    settings.CONTATO_RETENCAO_DIAS = 730
    antigo = criar_contato(nome="Antigo")
    envelhecer(antigo, 731)
    recente = criar_contato(nome="Recente")

    call_command("expurgar_contatos", verbosity=0)

    assert list(Contato.objects.values_list("pk", flat=True)) == [recente.pk]


def test_expurgo_preserva_quem_virou_cliente(settings):
    """A base legal muda para execucao de contrato; o prazo passa a ser o dele."""
    settings.CONTATO_RETENCAO_DIAS = 730
    convertido = criar_contato(nome="Cliente", situacao=Situacao.CONVERTIDO)
    envelhecer(convertido, 900)

    call_command("expurgar_contatos", verbosity=0)

    assert Contato.objects.filter(pk=convertido.pk).exists()


def test_expurgo_simulado_nao_apaga_nada(settings):
    settings.CONTATO_RETENCAO_DIAS = 30
    antigo = criar_contato()
    envelhecer(antigo, 60)

    call_command("expurgar_contatos", "--simular", verbosity=0)

    assert Contato.objects.count() == 1


# ---------------------------------------------------------------------------
# 3. Implantacao publica incompleta nao sobe
# ---------------------------------------------------------------------------


@override_settings(USE_HTTPS=True, CONTATO_CANAL_TITULAR="")
def test_implantacao_publica_sem_canal_do_titular_reprova():
    ids = {problema.id for problema in verificar_configuracao_publica(None)}

    assert CANAL_AUSENTE in ids


@override_settings(USE_HTTPS=True, CONTATO_CANAL_TITULAR="privacidade@exemplo.com.br")
def test_implantacao_publica_completa_passa():
    assert verificar_configuracao_publica(None) == []


@override_settings(USE_HTTPS=False, CONTATO_CANAL_TITULAR="")
def test_instalacao_local_nao_e_incomodada_pela_exigencia():
    """O gatilho e `USE_HTTPS`, e nao `DEBUG`: build e suite rodam sem TLS."""
    assert verificar_configuracao_publica(None) == []


@override_settings(CONTATO_RETENCAO_DIAS=0)
def test_retencao_zerada_e_erro_de_configuracao():
    ids = {problema.id for problema in verificar_configuracao_publica(None)}

    assert RETENCAO_INVALIDA in ids


def test_verificacao_esta_registrada_no_check_do_django():
    """Sem registro, as regras acima nunca rodariam no `manage.py check`."""
    call_command("check")
