"""A area interna: quem entra, quem nao entra e o que pode ser feito la."""

from __future__ import annotations

import pytest
from django.utils import timezone

from contatos.models import Contato, Situacao
from contatos.privacidade import AVISO_VERSAO
from tests.conftest import SENHA_DE_TESTE

pytestmark = pytest.mark.django_db


@pytest.fixture
def contato() -> Contato:
    return Contato.objects.create(
        nome="Maria Souza",
        email="maria@exemplo.com.br",
        telefone="11988887777",
        mensagem="Duas torres, portaria remota.",
        consentimento=True,
        consentimento_em=timezone.now(),
        aviso_versao=AVISO_VERSAO,
    )


# ---------------------------------------------------------------------------
# Autorizacao
# ---------------------------------------------------------------------------


def test_anonimo_vai_para_o_login(client, contato):
    resposta = client.get("/atendimento/")

    assert resposta.status_code == 302
    assert resposta["Location"].startswith("/login")
    assert "next=/atendimento/" in resposta["Location"]


def test_conta_sem_is_staff_recebe_403_e_nao_o_login(
    client, pessoa_sem_acesso, contato
):
    """Mandar quem ja esta logado de volta ao login sugere sessao caida."""
    client.force_login(pessoa_sem_acesso)

    assert client.get("/atendimento/").status_code == 403
    assert client.get(f"/atendimento/{contato.pk}/").status_code == 403


def test_atendente_ve_a_lista_e_o_detalhe(client, atendente, contato):
    client.force_login(atendente)

    lista = client.get("/atendimento/")
    detalhe = client.get(f"/atendimento/{contato.pk}/")

    assert lista.status_code == 200
    assert contato.protocolo in lista.content.decode("utf-8")
    assert detalhe.status_code == 200
    assert "Duas torres" in detalhe.content.decode("utf-8")


def test_o_menu_publico_oferece_o_login_e_nao_a_area_interna(client):
    """Para quem nao entrou, o item do menu e a porta -- e nao o nome da sala.

    O rotulo era "Atendimento" e apontava para `/atendimento/`, que devolvia o
    visitante ao login. Passou a ser "Login" e a apontar para `/login`: o
    destino e o mesmo, e agora o rotulo diz qual e.
    """
    corpo = client.get("/").content.decode("utf-8")

    assert 'href="/login"' in corpo
    assert ">Login</a>" in corpo
    assert 'href="/atendimento/"' not in corpo


def test_o_menu_da_equipe_troca_o_login_pelas_areas_internas(client, atendente):
    """Mostrar "Login" a quem ja entrou sugere que a sessao caiu."""
    client.force_login(atendente)

    corpo = client.get("/").content.decode("utf-8")

    assert 'href="/atendimento/"' in corpo
    assert 'href="/tarefas/"' in corpo
    assert ">Login</a>" not in corpo


def test_conta_sem_area_propria_nao_ve_atalho_para_area_interna(client, pessoa_sem_acesso):
    """O 403 ja recusaria a entrada; o menu nao deve convidar para ele."""
    client.force_login(pessoa_sem_acesso)

    corpo = client.get("/").content.decode("utf-8")

    assert 'href="/atendimento/"' not in corpo
    assert 'href="/tarefas/"' not in corpo


def test_login_recusa_credencial_errada_sem_dizer_qual_parte_errou(client, atendente):
    resposta = client.post(
        "/login", {"username": "atendente", "password": "errada"}
    )
    corpo = resposta.content.decode("utf-8")

    assert resposta.status_code == 200
    assert "Usuário ou senha inválidos." in corpo
    # A mensagem detalhada do Django nao e renderizada: dizer qual das duas
    # partes errou entrega ao visitante a lista de quem tem conta.
    assert "ambos os campos" not in corpo
    assert "both fields" not in corpo


def test_login_valido_passa_pelo_destino_derivado(client, atendente):
    """O destino sai da conta, e nao de um endereco fixo: e a emenda da area do cliente."""
    resposta = client.post(
        "/login", {"username": "atendente", "password": SENHA_DE_TESTE}
    )

    assert resposta.status_code == 302
    assert resposta["Location"] == "/apos-login"


def test_destino_derivado_manda_a_equipe_para_o_atendimento(client, atendente):
    client.force_login(atendente)

    resposta = client.get("/apos-login")

    assert resposta["Location"] == "/atendimento/"


def test_destino_derivado_de_conta_sem_area_volta_ao_site(client, pessoa_sem_acesso):
    """Enquanto a area do cliente nao existir, quem nao e da equipe fica no site."""
    client.force_login(pessoa_sem_acesso)

    resposta = client.get("/apos-login")

    assert resposta["Location"] == "/"


# ---------------------------------------------------------------------------
# Triagem
# ---------------------------------------------------------------------------


def test_situacao_muda_por_post(client, atendente, contato):
    client.force_login(atendente)

    resposta = client.post(
        f"/atendimento/{contato.pk}/situacao", {"situacao": Situacao.EM_ATENDIMENTO}
    )
    contato.refresh_from_db()

    assert resposta.status_code == 302
    assert contato.situacao == Situacao.EM_ATENDIMENTO


def test_situacao_desconhecida_e_recusada(client, atendente, contato):
    client.force_login(atendente)

    resposta = client.post(f"/atendimento/{contato.pk}/situacao", {"situacao": "vendido"})
    contato.refresh_from_db()

    assert resposta.status_code == 403
    assert contato.situacao == Situacao.NOVO


def test_triagem_nao_acontece_por_get(client, atendente, contato):
    client.force_login(atendente)

    assert client.get(f"/atendimento/{contato.pk}/situacao").status_code == 405


def test_triagem_sem_token_csrf_e_recusada(client_com_csrf, atendente, contato):
    client_com_csrf.force_login(atendente)

    resposta = client_com_csrf.post(
        f"/atendimento/{contato.pk}/situacao", {"situacao": Situacao.DESCARTADO}
    )
    contato.refresh_from_db()

    assert resposta.status_code == 403
    assert contato.situacao == Situacao.NOVO


# ---------------------------------------------------------------------------
# Direito de eliminacao (LGPD, art. 18, VI)
# ---------------------------------------------------------------------------


def test_exclusao_apaga_o_registro(client, atendente, contato):
    client.force_login(atendente)

    resposta = client.post(f"/atendimento/{contato.pk}/excluir")

    assert resposta.status_code == 302
    assert Contato.objects.count() == 0


def test_exclusao_exige_conta_de_atendimento(client, pessoa_sem_acesso, contato):
    client.force_login(pessoa_sem_acesso)

    assert client.post(f"/atendimento/{contato.pk}/excluir").status_code == 403
    assert Contato.objects.count() == 1
