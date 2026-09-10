"""Responsável pelo atendimento (ADR 0005 fase 5).

Uma conta pode ser a "caixa de entrada": toda solicitação nova do formulário
público cai para ela. E qualquer conta da equipe pode passar uma solicitação
para outra na ficha.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from contatos.models import Contato
from contatos.privacidade import AVISO_VERSAO

pytestmark = pytest.mark.django_db


@pytest.fixture
def contato() -> Contato:
    return Contato.objects.create(
        nome="Maria Souza",
        email="maria@exemplo.com.br",
        telefone="11988887777",
        mensagem="Portaria remota.",
        consentimento=True,
        consentimento_em=timezone.now(),
        aviso_versao=AVISO_VERSAO,
    )


# ---------------------------------------------------------------------------
# Chegada: cai na caixa de entrada designada
# ---------------------------------------------------------------------------


def test_contato_novo_cai_na_caixa_de_entrada(client, atendente, envio_valido):
    atendente.recebe_novos_contatos = True
    atendente.save()

    client.post("/contato", data=envio_valido)

    assert Contato.objects.get().responsavel == atendente


def test_contato_novo_sem_caixa_definida_entra_sem_dono(client, envio_valido):
    client.post("/contato", data=envio_valido)

    assert Contato.objects.get().responsavel is None


def test_caixa_de_entrada_inativa_nao_recebe(client, atendente, envio_valido):
    atendente.recebe_novos_contatos = True
    atendente.is_active = False
    atendente.save()

    client.post("/contato", data=envio_valido)

    assert Contato.objects.get().responsavel is None


# ---------------------------------------------------------------------------
# Reatribuicao na ficha
# ---------------------------------------------------------------------------


def test_passar_para_outra_conta_da_equipe(client, atendente, contato, django_user_model):
    colega = django_user_model.objects.create_user(
        username="colega", password="senha-de-teste-longa-2026", is_staff=True
    )
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/atendimento/{contato.pk}/responsavel", {"responsavel": str(colega.pk)}
    )
    contato.refresh_from_db()

    assert resposta.status_code == 302
    assert contato.responsavel == colega


def test_passar_para_ninguem_tira_o_dono(client, atendente, contato):
    contato.responsavel = atendente
    contato.save()
    client.force_login(atendente)

    client.post(f"/painel/atendimento/{contato.pk}/responsavel", {"responsavel": ""})
    contato.refresh_from_db()

    assert contato.responsavel is None


def test_nao_da_para_atribuir_a_conta_sem_is_staff(client, atendente, contato, pessoa_sem_acesso):
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/atendimento/{contato.pk}/responsavel",
        {"responsavel": str(pessoa_sem_acesso.pk)},
    )
    contato.refresh_from_db()

    assert resposta.status_code == 403
    assert contato.responsavel is None


def test_reatribuir_nao_acontece_por_get(client, atendente, contato):
    client.force_login(atendente)

    assert client.get(f"/painel/atendimento/{contato.pk}/responsavel").status_code == 405


def test_conta_sem_is_staff_nao_reatribui(client, pessoa_sem_acesso, contato):
    client.force_login(pessoa_sem_acesso)

    resposta = client.post(
        f"/painel/atendimento/{contato.pk}/responsavel", {"responsavel": ""}
    )

    assert resposta.status_code == 403


# ---------------------------------------------------------------------------
# Lista: "so as minhas"
# ---------------------------------------------------------------------------


def test_filtro_meus_mostra_so_os_atribuidos_a_mim(client, atendente, django_user_model):
    colega = django_user_model.objects.create_user(
        username="colega", password="senha-de-teste-longa-2026", is_staff=True
    )
    meu = Contato.objects.create(
        nome="Cliente A", email="a@exemplo.com", telefone="1", mensagem="",
        consentimento=True, consentimento_em=timezone.now(), aviso_versao=AVISO_VERSAO,
        responsavel=atendente,
    )
    dele = Contato.objects.create(
        nome="Cliente B", email="b@exemplo.com", telefone="2", mensagem="",
        consentimento=True, consentimento_em=timezone.now(), aviso_versao=AVISO_VERSAO,
        responsavel=colega,
    )
    client.force_login(atendente)

    corpo = client.get("/painel/atendimento/?meus=1").content.decode("utf-8")

    assert meu.protocolo in corpo
    assert dele.protocolo not in corpo
