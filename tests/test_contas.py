"""O CRUD de contas: quem entra, o que a senha exige, e a trava de nao se trancar fora.

Como o resto da suite, toca o banco de verdade. A tela substitui
`manage.py createsuperuser` (ADR 0005 fase 4); o projeto continua sem
`django.contrib.admin`.
"""

from __future__ import annotations

import pytest

from tests.conftest import SENHA_DE_TESTE

pytestmark = pytest.mark.django_db

# Forte o bastante para os validadores de `AUTH_PASSWORD_VALIDATORS`
# (min 12, nao-so-numeros, nao-comum, nao-parecida-com-a-conta).
SENHA_FORTE = "tribunal-verde-8821"


# ---------------------------------------------------------------------------
# Autorizacao
# ---------------------------------------------------------------------------


def test_anonimo_vai_para_o_login(client):
    resposta = client.get("/painel/contas/")

    assert resposta.status_code == 302
    assert resposta["Location"].startswith("/login")
    assert "next=/painel/contas/" in resposta["Location"]


def test_conta_sem_is_staff_recebe_403(client, pessoa_sem_acesso, atendente):
    """`is_staff` guarda a administracao -- criar conta e a acao mais sensivel daqui."""
    client.force_login(pessoa_sem_acesso)

    assert client.get("/painel/contas/").status_code == 403
    assert client.get("/painel/contas/nova").status_code == 403
    assert client.get(f"/painel/contas/{atendente.pk}/").status_code == 403


def test_admin_ve_a_lista(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    corpo = client.get("/painel/contas/").content.decode("utf-8")

    assert "atendente" in corpo
    assert "visitante" in corpo


def test_a_barra_do_painel_mostra_contas_so_para_admin(
    client, atendente, pessoa_sem_acesso
):
    client.force_login(atendente)
    com = client.get("/painel/tarefas/").content.decode("utf-8")
    client.force_login(pessoa_sem_acesso)
    sem = client.get("/painel/tarefas/").content.decode("utf-8")

    assert 'href="/painel/contas/"' in com
    assert 'href="/painel/contas/"' not in sem


# ---------------------------------------------------------------------------
# Criar
# ---------------------------------------------------------------------------


def test_criar_conta_grava_ativa_e_com_senha_utilizavel(client, atendente, django_user_model):
    client.force_login(atendente)

    resposta = client.post(
        "/painel/contas/nova",
        {
            "username": "luiz",
            "first_name": "Luiz",
            "last_name": "Prado",
            "senha": SENHA_FORTE,
        },
    )

    assert resposta.status_code == 302
    conta = django_user_model.objects.get(username="luiz")
    assert conta.is_active is True
    assert conta.is_staff is False
    assert conta.check_password(SENHA_FORTE)


def test_criar_conta_com_is_staff(client, atendente, django_user_model):
    client.force_login(atendente)

    client.post(
        "/painel/contas/nova",
        {"username": "socio", "senha": SENHA_FORTE, "is_staff": "on"},
    )

    assert django_user_model.objects.get(username="socio").is_staff is True


def test_senha_fraca_e_recusada_e_nada_e_gravado(client, atendente, django_user_model):
    client.force_login(atendente)

    resposta = client.post(
        "/painel/contas/nova",
        {"username": "marcelo", "senha": "curta"},
    )

    assert resposta.status_code == 200
    assert not django_user_model.objects.filter(username="marcelo").exists()


def test_senha_parecida_com_o_login_e_recusada(client, atendente, django_user_model):
    """`validate_password` recebe a instancia, entao a similaridade e checada."""
    client.force_login(atendente)

    resposta = client.post(
        "/painel/contas/nova",
        {"username": "joana.ribeiro", "senha": "joana.ribeiro"},
    )

    assert resposta.status_code == 200
    assert not django_user_model.objects.filter(username="joana.ribeiro").exists()


def test_login_repetido_e_recusado(client, atendente, django_user_model):
    client.force_login(atendente)

    resposta = client.post(
        "/painel/contas/nova",
        {"username": "atendente", "senha": SENHA_FORTE},
    )

    assert resposta.status_code == 200
    assert django_user_model.objects.filter(username="atendente").count() == 1


# ---------------------------------------------------------------------------
# Editar
# ---------------------------------------------------------------------------


def test_editar_troca_nome_e_papel(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/contas/{pessoa_sem_acesso.pk}/",
        {
            "first_name": "Vera",
            "last_name": "Lima",
            "is_staff": "on",
            "is_active": "on",
        },
    )
    pessoa_sem_acesso.refresh_from_db()

    assert resposta.status_code == 302
    assert pessoa_sem_acesso.get_full_name() == "Vera Lima"
    assert pessoa_sem_acesso.is_staff is True


def test_editar_com_nova_senha_troca_a_senha(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    client.post(
        f"/painel/contas/{pessoa_sem_acesso.pk}/",
        {"is_active": "on", "nova_senha": SENHA_FORTE},
    )
    pessoa_sem_acesso.refresh_from_db()

    assert pessoa_sem_acesso.check_password(SENHA_FORTE)


def test_editar_sem_nova_senha_mantem_a_atual(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    client.post(
        f"/painel/contas/{pessoa_sem_acesso.pk}/",
        {"first_name": "Nome", "is_active": "on"},
    )
    pessoa_sem_acesso.refresh_from_db()

    assert pessoa_sem_acesso.check_password(SENHA_DE_TESTE)


def test_desativar_uma_conta_tira_o_acesso(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    client.post(f"/painel/contas/{pessoa_sem_acesso.pk}/", {"first_name": ""})
    pessoa_sem_acesso.refresh_from_db()

    assert pessoa_sem_acesso.is_active is False


def test_nao_da_para_desativar_a_propria_conta(client, atendente):
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/contas/{atendente.pk}/",
        {"is_staff": "on"},  # is_active ausente = desmarcado
    )
    atendente.refresh_from_db()

    assert resposta.status_code == 200
    assert atendente.is_active is True


def test_nao_da_para_remover_o_proprio_is_staff(client, atendente):
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/contas/{atendente.pk}/",
        {"is_active": "on"},  # is_staff ausente = desmarcado
    )
    atendente.refresh_from_db()

    assert resposta.status_code == 200
    assert atendente.is_staff is True


def test_marcar_a_caixa_de_atendimento_desmarca_a_anterior(
    client, atendente, django_user_model
):
    """No maximo uma caixa de entrada (ADR 0005 fase 5)."""
    antiga = django_user_model.objects.create_user(
        username="antiga", password=SENHA_DE_TESTE, is_staff=True,
        recebe_novos_contatos=True,
    )
    client.force_login(atendente)

    client.post(
        f"/painel/contas/{atendente.pk}/",
        {"is_staff": "on", "is_active": "on", "recebe_novos_contatos": "on"},
    )
    antiga.refresh_from_db()
    atendente.refresh_from_db()

    assert atendente.recebe_novos_contatos is True
    assert antiga.recebe_novos_contatos is False


def test_caixa_de_atendimento_exige_is_staff(client, atendente, pessoa_sem_acesso):
    client.force_login(atendente)

    resposta = client.post(
        f"/painel/contas/{pessoa_sem_acesso.pk}/",
        {"is_active": "on", "recebe_novos_contatos": "on"},  # sem is_staff
    )
    pessoa_sem_acesso.refresh_from_db()

    assert resposta.status_code == 200
    assert pessoa_sem_acesso.recebe_novos_contatos is False


def test_nenhuma_tela_de_conta_vaza_sintaxe_de_template(client, atendente):
    client.force_login(atendente)

    for caminho in ("/painel/contas/", "/painel/contas/nova", f"/painel/contas/{atendente.pk}/"):
        corpo = client.get(caminho).content.decode("utf-8")
        for marca in ("{#", "{%", "{{"):
            assert marca not in corpo, f"{caminho} vazou {marca}"
