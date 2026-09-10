"""O modulo de tarefas: quem entra, o que o banco recusa e o que fica de rastro.

Como o resto da suite, estes testes tocam o PostgreSQL de verdade -- as
`CheckConstraint` so significam alguma coisa se forem exercitadas contra o
banco que as aplica.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from tarefas.models import Andamento, Prioridade, Situacao, Tarefa

pytestmark = pytest.mark.django_db


@pytest.fixture
def tarefa(atendente) -> Tarefa:
    return Tarefa.objects.create(
        titulo="Renovar contrato de monitoramento",
        descricao="Vence no fim do mes.",
        responsavel=atendente,
        criado_por=atendente,
        prazo=dt.date(2026, 12, 31),
    )


# ---------------------------------------------------------------------------
# Autorizacao
# ---------------------------------------------------------------------------


def test_anonimo_vai_para_o_login(client, tarefa):
    resposta = client.get("/tarefas/")

    assert resposta.status_code == 302
    assert resposta["Location"].startswith("/login")
    assert "next=/tarefas/" in resposta["Location"]


def test_conta_sem_is_staff_recebe_403_em_toda_a_area(client, pessoa_sem_acesso, tarefa):
    """A conta de cliente do ADR 0002 tambem sera autenticada."""
    client.force_login(pessoa_sem_acesso)

    assert client.get("/tarefas/").status_code == 403
    assert client.get(f"/tarefas/{tarefa.pk}/").status_code == 403
    assert client.get("/tarefas/nova").status_code == 403
    assert client.get(f"/tarefas/{tarefa.pk}/editar").status_code == 403
    assert client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": "concluida"}).status_code == 403
    assert client.post(f"/tarefas/{tarefa.pk}/andamento", {"texto": "oi"}).status_code == 403


def test_equipe_ve_a_lista_e_a_ficha(client, atendente, tarefa):
    client.force_login(atendente)

    lista = client.get("/tarefas/")
    ficha = client.get(f"/tarefas/{tarefa.pk}/")

    assert lista.status_code == 200
    assert "Renovar contrato" in lista.content.decode("utf-8")
    assert ficha.status_code == 200
    assert "Vence no fim do mes." in ficha.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Restricoes de banco
# ---------------------------------------------------------------------------


def test_concluida_sem_data_de_conclusao_e_recusada(atendente):
    """`tarefa_conclusao_coerente`: as duas colunas nao podem divergir."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Tarefa.objects.create(
            titulo="Incoerente",
            responsavel=atendente,
            criado_por=atendente,
            situacao=Situacao.CONCLUIDA,
            concluida_em=None,
        )


def test_data_de_conclusao_em_tarefa_aberta_e_recusada(atendente):
    with pytest.raises(IntegrityError), transaction.atomic():
        Tarefa.objects.create(
            titulo="Tambem incoerente",
            responsavel=atendente,
            criado_por=atendente,
            situacao=Situacao.A_FAZER,
            concluida_em=timezone.now(),
        )


def test_situacao_desconhecida_nao_entra_no_banco(atendente):
    with pytest.raises(IntegrityError), transaction.atomic():
        Tarefa.objects.create(
            titulo="Situacao invalida",
            responsavel=atendente,
            criado_por=atendente,
            situacao="arquivada",
        )


def test_titulo_vazio_e_recusado(atendente):
    with pytest.raises(IntegrityError), transaction.atomic():
        Tarefa.objects.create(titulo="", responsavel=atendente, criado_por=atendente)


def test_prioridade_fora_do_catalogo_e_recusada(atendente):
    with pytest.raises(IntegrityError), transaction.atomic():
        Tarefa.objects.create(
            titulo="Prioridade invalida",
            responsavel=atendente,
            criado_por=atendente,
            prioridade=9,
        )


# ---------------------------------------------------------------------------
# Situacao e rastro
# ---------------------------------------------------------------------------


def test_concluir_preenche_a_data_e_reabrir_a_limpa(client, atendente, tarefa):
    """O metodo `aplicar_situacao` e o unico caminho, e a restricao cobra isso."""
    client.force_login(atendente)

    client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": Situacao.CONCLUIDA})
    tarefa.refresh_from_db()
    assert tarefa.situacao == Situacao.CONCLUIDA
    assert tarefa.concluida_em is not None

    client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": Situacao.EM_ANDAMENTO})
    tarefa.refresh_from_db()
    assert tarefa.situacao == Situacao.EM_ANDAMENTO
    assert tarefa.concluida_em is None


def test_mudanca_de_situacao_vira_linha_de_andamento(client, atendente, tarefa):
    client.force_login(atendente)

    client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": Situacao.EM_ANDAMENTO})

    andamento = tarefa.andamentos.get()
    assert andamento.automatico is True
    assert andamento.autor == atendente
    assert "Em andamento" in andamento.texto


def test_situacao_repetida_nao_gera_andamento(client, atendente, tarefa):
    """Salvar sem mudar nada nao deve encher a linha do tempo de ruido."""
    client.force_login(atendente)

    client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": Situacao.A_FAZER})

    assert tarefa.andamentos.count() == 0


def test_situacao_desconhecida_e_recusada_pela_view(client, atendente, tarefa):
    client.force_login(atendente)

    resposta = client.post(f"/tarefas/{tarefa.pk}/situacao", {"situacao": "arquivada"})
    tarefa.refresh_from_db()

    assert resposta.status_code == 403
    assert tarefa.situacao == Situacao.A_FAZER


def test_triagem_nao_acontece_por_get(client, atendente, tarefa):
    client.force_login(atendente)

    assert client.get(f"/tarefas/{tarefa.pk}/situacao").status_code == 405


def test_mudanca_sem_token_csrf_e_recusada(client_com_csrf, atendente, tarefa):
    client_com_csrf.force_login(atendente)

    resposta = client_com_csrf.post(
        f"/tarefas/{tarefa.pk}/situacao", {"situacao": Situacao.CONCLUIDA}
    )
    tarefa.refresh_from_db()

    assert resposta.status_code == 403
    assert tarefa.situacao == Situacao.A_FAZER


# ---------------------------------------------------------------------------
# Cadastro e andamento
# ---------------------------------------------------------------------------


def test_criar_tarefa_grava_e_registra_quem_criou(client, atendente):
    client.force_login(atendente)

    resposta = client.post(
        "/tarefas/nova",
        {
            "titulo": "Trocar as cameras da portaria",
            "descricao": "Duas unidades sem imagem.",
            "responsavel": atendente.pk,
            "prazo": "2026-10-15",
            "prioridade": Prioridade.ALTA,
        },
    )

    tarefa = Tarefa.objects.get(titulo="Trocar as cameras da portaria")
    assert resposta.status_code == 302
    assert resposta["Location"] == f"/tarefas/{tarefa.pk}/"
    assert tarefa.criado_por == atendente
    assert tarefa.prazo == dt.date(2026, 10, 15)
    assert tarefa.prioridade == Prioridade.ALTA
    assert tarefa.andamentos.filter(automatico=True).exists()


def test_tarefa_sem_titulo_nao_e_criada(client, atendente):
    client.force_login(atendente)

    resposta = client.post(
        "/tarefas/nova",
        {"titulo": "   ", "responsavel": atendente.pk, "prioridade": Prioridade.NORMAL},
    )

    assert resposta.status_code == 200
    assert Tarefa.objects.count() == 0


def test_conta_sem_is_staff_nao_pode_ser_responsavel(client, atendente, pessoa_sem_acesso):
    """O seletor lista so a equipe; enviar outro id nao pode contornar isso."""
    client.force_login(atendente)

    resposta = client.post(
        "/tarefas/nova",
        {
            "titulo": "Tarefa para quem nao e da equipe",
            "responsavel": pessoa_sem_acesso.pk,
            "prioridade": Prioridade.NORMAL,
        },
    )

    assert resposta.status_code == 200
    assert Tarefa.objects.count() == 0


def test_andamento_registra_autor_e_nao_e_automatico(client, atendente, tarefa):
    client.force_login(atendente)

    resposta = client.post(
        f"/tarefas/{tarefa.pk}/andamento",
        {"texto": "Fornecedor respondeu, proposta na sexta."},
    )

    andamento = Andamento.objects.get()
    assert resposta.status_code == 302
    assert andamento.autor == atendente
    assert andamento.automatico is False
    assert "Fornecedor respondeu" in andamento.texto


def test_andamento_vazio_volta_para_a_ficha_sem_gravar(client, atendente, tarefa):
    client.force_login(atendente)

    resposta = client.post(f"/tarefas/{tarefa.pk}/andamento", {"texto": "   "})

    assert resposta.status_code == 400
    assert Andamento.objects.count() == 0


def test_troca_de_responsavel_fica_escrita(client, atendente, tarefa, django_user_model):
    outro = django_user_model.objects.create_user(
        username="colega", password="senha-de-teste-longa-2026", is_staff=True
    )
    client.force_login(atendente)

    client.post(
        f"/tarefas/{tarefa.pk}/editar",
        {
            "titulo": tarefa.titulo,
            "descricao": tarefa.descricao,
            "responsavel": outro.pk,
            "prazo": "2026-12-31",
            "prioridade": Prioridade.NORMAL,
        },
    )
    tarefa.refresh_from_db()

    assert tarefa.responsavel == outro
    assert tarefa.andamentos.filter(automatico=True, texto__contains="colega").exists()


# ---------------------------------------------------------------------------
# Lista: filtro e atraso
# ---------------------------------------------------------------------------


def test_lista_esconde_concluidas_por_padrao_mas_diz_que_esconde(client, atendente, tarefa):
    """Filtro padrao que esconde sem avisar e como perder tarefa."""
    tarefa.aplicar_situacao(Situacao.CONCLUIDA)
    tarefa.save()
    client.force_login(atendente)

    corpo = client.get("/tarefas/").content.decode("utf-8")

    assert "Renovar contrato" not in corpo
    assert 'value="abertas" selected' in corpo


def test_filtro_todas_mostra_a_concluida(client, atendente, tarefa):
    tarefa.aplicar_situacao(Situacao.CONCLUIDA)
    tarefa.save()
    client.force_login(atendente)

    corpo = client.get("/tarefas/?situacao=todas").content.decode("utf-8")

    assert "Renovar contrato" in corpo


def test_filtro_desconhecido_nao_quebra_a_lista(client, atendente, tarefa):
    client.force_login(atendente)

    resposta = client.get("/tarefas/?situacao=inventada&responsavel=abc")

    assert resposta.status_code == 200
    assert "Renovar contrato" in resposta.content.decode("utf-8")


def test_atraso_so_vale_para_tarefa_aberta(atendente):
    vencida = Tarefa.objects.create(
        titulo="Vencida",
        responsavel=atendente,
        criado_por=atendente,
        prazo=timezone.localdate() - dt.timedelta(days=1),
    )
    assert vencida.esta_atrasada is True

    vencida.aplicar_situacao(Situacao.CONCLUIDA)
    vencida.save()
    assert vencida.esta_atrasada is False

    vencida.aplicar_situacao(Situacao.CANCELADA)
    vencida.save()
    assert vencida.esta_atrasada is False


def test_tarefa_sem_prazo_nunca_esta_atrasada(atendente):
    sem_prazo = Tarefa.objects.create(
        titulo="Sem prazo", responsavel=atendente, criado_por=atendente
    )

    assert sem_prazo.esta_atrasada is False


def test_ordenacao_poe_quem_nao_tem_prazo_por_ultimo(client, atendente):
    Tarefa.objects.create(titulo="Sem prazo", responsavel=atendente, criado_por=atendente)
    Tarefa.objects.create(
        titulo="Com prazo",
        responsavel=atendente,
        criado_por=atendente,
        prazo=timezone.localdate() + dt.timedelta(days=5),
    )
    client.force_login(atendente)

    corpo = client.get("/tarefas/").content.decode("utf-8")

    assert corpo.index("Com prazo") < corpo.index("Sem prazo")


# ---------------------------------------------------------------------------
# Casca
# ---------------------------------------------------------------------------


def test_os_rotulos_do_formulario_levam_acento(client, atendente):
    """"Descricao" e "Responsavel" saiam na tela, e a suite inteira passava.

    O Django deriva o rotulo do nome do atributo, e nome de atributo e ASCII
    por regra da casa -- entao o rotulo so tem acento com `verbose_name`
    explicito. Quem viu foi o navegador; esta asercao e para nao precisar do
    navegador de novo.
    """
    client.force_login(atendente)

    corpo = client.get("/tarefas/nova").content.decode("utf-8")

    assert ">Título</label>" in corpo
    assert ">Descrição</label>" in corpo
    assert ">Responsável</label>" in corpo
    for sem_acento in (">Descricao<", ">Responsavel<", ">Titulo<"):
        assert sem_acento not in corpo


def test_a_pessoa_aparece_pelo_nome_e_nao_pelo_login(client, atendente, django_user_model):
    """Nome de login serve para autenticar, nao para conversar."""
    atendente.first_name = "Maria"
    atendente.last_name = "Souza"
    atendente.save()
    client.force_login(atendente)

    corpo = client.get("/tarefas/nova").content.decode("utf-8")

    assert "Maria Souza" in corpo
    assert ">atendente</option>" not in corpo


def test_nenhuma_tela_de_tarefa_vaza_sintaxe_de_template(client, atendente, tarefa):
    client.force_login(atendente)

    caminhos = [
        "/tarefas/",
        "/tarefas/nova",
        f"/tarefas/{tarefa.pk}/",
        f"/tarefas/{tarefa.pk}/editar",
    ]
    for caminho in caminhos:
        corpo = client.get(caminho).content.decode("utf-8")
        for marca in ("{#", "{%", "{{"):
            assert marca not in corpo, f"{caminho} vazou {marca}"
