"""`POST /contato`: quem pode enviar, o que e recusado e o que e gravado."""

from __future__ import annotations

import json

import pytest

from contatos.forms import CAMPO_ARMADILHA
from contatos.limites import resumo_de_endereco
from contatos.models import Contato
from contatos.privacidade import AVISO_VERSAO
from tests.conftest import ORIGEM_DO_SITE, ORIGEM_ESTRANHA

pytestmark = pytest.mark.django_db


def enviar(client, dados, *, origem=ORIGEM_DO_SITE, json_=False):
    if json_:
        return client.post(
            "/contato",
            data=json.dumps(dados),
            content_type="application/json",
            headers={"origin": origem, "accept": "application/json"},
        )
    return client.post("/contato", data=dados, headers={"origin": origem})


# ---------------------------------------------------------------------------
# Caminho feliz
# ---------------------------------------------------------------------------


def test_envio_valido_grava_e_redireciona(client, origens, envio_valido):
    resposta = enviar(client, envio_valido)

    assert resposta.status_code == 303
    assert resposta["Location"] == "/contato/recebido"

    contato = Contato.objects.get()
    assert contato.nome == "Maria Souza"
    assert contato.email == "maria@exemplo.com.br"
    assert contato.segmento == "condominios"
    assert contato.solucoes == ["portaria", "facilities"]
    assert contato.situacao == "novo"


def test_envio_por_json_devolve_protocolo(client, origens, envio_valido):
    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["protocolo"] == Contato.objects.get().protocolo
    assert corpo["protocolo"].startswith("MP-")


def test_consentimento_e_gravado_com_a_versao_do_aviso(client, origens, envio_valido):
    enviar(client, envio_valido)

    contato = Contato.objects.get()
    assert contato.consentimento is True
    assert contato.consentimento_em is not None
    # Sem isto nao ha como responder, um ano depois, a qual texto a pessoa
    # consentiu.
    assert contato.aviso_versao == AVISO_VERSAO


def test_endereco_de_rede_e_guardado_como_resumo_e_nunca_em_claro(
    client, origens, envio_valido
):
    enviar(client, envio_valido)

    contato = Contato.objects.get()
    assert contato.ip_hash == resumo_de_endereco("127.0.0.1")
    assert "127.0.0.1" not in contato.ip_hash
    assert len(contato.ip_hash) == 64


def test_resposta_traz_os_cabecalhos_de_cors_da_origem_validada(
    client, origens, envio_valido
):
    resposta = enviar(client, envio_valido, json_=True)

    assert resposta["Access-Control-Allow-Origin"] == ORIGEM_DO_SITE
    # Nunca `*`, e por isso a resposta precisa variar por origem.
    assert "Origin" in resposta["Vary"]
    # Credencial NAO e liberada: a rota e sem sessao.
    assert "Access-Control-Allow-Credentials" not in resposta


# ---------------------------------------------------------------------------
# Origem: a defesa que substitui o CSRF nesta rota
# ---------------------------------------------------------------------------


def test_origem_desconhecida_e_recusada_sem_gravar(client, origens, envio_valido):
    resposta = enviar(client, envio_valido, origem=ORIGEM_ESTRANHA)

    assert resposta.status_code == 403
    assert Contato.objects.count() == 0


def test_envio_sem_cabecalho_origin_e_recusado(client, origens, envio_valido):
    resposta = client.post("/contato", data=envio_valido)

    assert resposta.status_code == 403
    assert Contato.objects.count() == 0


def test_lista_de_origens_vazia_recusa_tudo(client, settings, envio_valido):
    """Fechado por padrao: esquecer de configurar vira 403, nao rota aberta."""
    settings.CONTATO_ORIGENS_PERMITIDAS = ()
    settings.DEBUG = False

    resposta = enviar(client, envio_valido)

    assert resposta.status_code == 403
    assert Contato.objects.count() == 0


def test_origem_e_comparada_por_igualdade_e_nao_por_sufixo(
    client, origens, envio_valido
):
    resposta = enviar(client, envio_valido, origem=ORIGEM_DO_SITE + ".invasor.com")

    assert resposta.status_code == 403


def test_prevoo_responde_204_para_origem_valida(client, origens):
    resposta = client.options("/contato", headers={"origin": ORIGEM_DO_SITE})

    assert resposta.status_code == 204
    assert resposta["Access-Control-Allow-Origin"] == ORIGEM_DO_SITE
    assert "POST" in resposta["Access-Control-Allow-Methods"]


def test_prevoo_de_origem_invalida_nao_libera_nada(client, origens):
    resposta = client.options("/contato", headers={"origin": ORIGEM_ESTRANHA})

    assert resposta.status_code == 403
    assert "Access-Control-Allow-Origin" not in resposta


def test_metodo_get_nao_e_aceito(client, origens):
    assert client.get("/contato", headers={"origin": ORIGEM_DO_SITE}).status_code == 405


# ---------------------------------------------------------------------------
# Robo e abuso
# ---------------------------------------------------------------------------


def test_campo_armadilha_preenchido_nao_grava_e_nao_denuncia(
    client, origens, envio_valido
):
    """A resposta e IDENTICA a de um envio valido, de proposito."""
    envio_valido[CAMPO_ARMADILHA] = "robo"

    resposta = enviar(client, envio_valido)

    assert resposta.status_code == 303
    assert resposta["Location"] == "/contato/recebido"
    assert Contato.objects.count() == 0


def test_limite_por_origem_de_rede_responde_429(client, origens, envio_valido):
    for indice in range(5):
        envio_valido["email"] = f"pessoa{indice}@exemplo.com.br"
        assert enviar(client, envio_valido).status_code == 303

    envio_valido["email"] = "excedente@exemplo.com.br"
    resposta = enviar(client, envio_valido)

    assert resposta.status_code == 429
    assert resposta["Retry-After"] == "900"
    assert Contato.objects.count() == 5


def test_limite_conta_apenas_a_janela_configurada(client, origens, envio_valido, settings):
    settings.CONTATO_MAX_POR_JANELA = 1
    assert enviar(client, envio_valido).status_code == 303
    assert enviar(client, envio_valido).status_code == 429

    # Janela deslizante: alargar o teto volta a aceitar sem apagar nada.
    settings.CONTATO_MAX_POR_JANELA = 3
    assert enviar(client, envio_valido).status_code == 303


# ---------------------------------------------------------------------------
# Validacao
# ---------------------------------------------------------------------------


def test_sem_consentimento_nao_grava(client, origens, envio_valido):
    del envio_valido["consentimento"]

    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 400
    assert "consentimento" in resposta.json()["campos"]
    assert Contato.objects.count() == 0


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nome", ""),
        ("email", "nao-e-email"),
        ("telefone", "sem digitos"),
    ],
)
def test_campo_invalido_reprova_o_envio(client, origens, envio_valido, campo, valor):
    envio_valido[campo] = valor

    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 400
    assert campo in resposta.json()["campos"]
    assert Contato.objects.count() == 0


def test_solucao_fora_do_catalogo_e_recusada(client, origens, envio_valido):
    envio_valido["solucoes"] = ["portaria", "helicoptero"]

    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 400
    assert "solucoes" in resposta.json()["campos"]


def test_mensagem_acima_do_teto_e_recusada(client, origens, envio_valido, settings):
    settings.CONTATO_TAMANHO_MAXIMO_MENSAGEM = 50
    envio_valido["mensagem"] = "a" * 51

    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 400
    assert "mensagem" in resposta.json()["campos"]


def test_corpo_json_invalido_nao_derruba_a_rota(client, origens):
    resposta = client.post(
        "/contato",
        data="{isto nao e json",
        content_type="application/json",
        headers={"origin": ORIGEM_DO_SITE, "accept": "application/json"},
    )

    assert resposta.status_code == 400
    assert Contato.objects.count() == 0


def test_solucao_unica_em_json_nao_vira_lista_de_letras(client, origens, envio_valido):
    """Dicionario nao tem `getlist`; sem normalizar, "portaria" viraria 8 itens."""
    envio_valido["solucoes"] = "portaria"

    resposta = enviar(client, envio_valido, json_=True)

    assert resposta.status_code == 201
    assert Contato.objects.get().solucoes == ["portaria"]
