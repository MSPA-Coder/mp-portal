"""A pagina `/contato`: mostra o formulario (GET) e recebe o envio (POST).

Depois da incorporacao do site ao portal, formulario e destino sao a MESMA
rota. Isso trocou a lista de origens e o CORS pelo CSRF do Django -- o gatilho
estava escrito no ADR 0001 e disparou. O que sobrou de defesa proprio desta
rota: campo-armadilha, limite por resumo de endereco e corpo pequeno.
"""

from __future__ import annotations

import pytest

from contatos.forms import CAMPO_ARMADILHA
from contatos.limites import resumo_de_endereco
from contatos.models import Contato
from contatos.privacidade import AVISO_VERSAO

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# A pagina
# ---------------------------------------------------------------------------


def test_pagina_de_contato_e_publica_e_traz_o_formulario(client):
    resposta = client.get("/contato")
    corpo = resposta.content.decode("utf-8")

    assert resposta.status_code == 200
    assert 'id="ctaForm"' in corpo
    assert 'name="csrfmiddlewaretoken"' in corpo
    # O consentimento e a base legal declarada: sem a caixa, o formulario nao
    # tem como ser enviado dentro da lei.
    assert 'name="consentimento"' in corpo
    assert "aviso de privacidade" in corpo


def test_pagina_de_contato_nao_promete_mais_do_que_cumpre(client):
    """O texto de rascunho saiu junto com o backend de verdade."""
    corpo = client.get("/contato").content.decode("utf-8")

    assert "não está conectado" not in corpo
    assert "nada foi enviado" not in corpo.lower()


def test_catalogo_do_formulario_usa_codigos_estaveis(client):
    """O rotulo muda quando a comunicacao mudar; o codigo gravado nao pode."""
    corpo = client.get("/contato").content.decode("utf-8")

    assert 'value="seguranca_eletronica"' in corpo
    assert 'value="condominios"' in corpo
    assert 'name="solucoes"' in corpo
    assert 'name="sol"' not in corpo


# ---------------------------------------------------------------------------
# O envio
# ---------------------------------------------------------------------------


def test_envio_valido_grava_e_redireciona(client, envio_valido):
    resposta = client.post("/contato", data=envio_valido)

    assert resposta.status_code == 303
    assert resposta["Location"] == "/contato/recebido"

    registro = Contato.objects.get()
    assert registro.nome == "Maria Souza"
    assert registro.email == "maria@exemplo.com.br"
    assert registro.segmento == "condominios"
    assert registro.solucoes == ["portaria", "facilities"]
    assert registro.situacao == "novo"


def test_consentimento_e_gravado_com_a_versao_do_aviso(client, envio_valido):
    client.post("/contato", data=envio_valido)

    registro = Contato.objects.get()
    assert registro.consentimento is True
    assert registro.consentimento_em is not None
    # Sem isto nao ha como responder, um ano depois, a qual texto a pessoa
    # consentiu.
    assert registro.aviso_versao == AVISO_VERSAO


def test_endereco_de_rede_e_guardado_como_resumo_e_nunca_em_claro(client, envio_valido):
    client.post("/contato", data=envio_valido)

    registro = Contato.objects.get()
    assert registro.ip_hash == resumo_de_endereco("127.0.0.1")
    assert "127.0.0.1" not in registro.ip_hash
    assert len(registro.ip_hash) == 64


def test_envio_sem_token_csrf_e_recusado(client_com_csrf, envio_valido):
    """A defesa que substituiu a lista de origens quando as duas metades viraram uma."""
    resposta = client_com_csrf.post("/contato", data=envio_valido)

    assert resposta.status_code == 403
    assert Contato.objects.count() == 0


def test_metodos_alem_de_get_e_post_sao_recusados(client):
    assert client.delete("/contato").status_code == 405
    assert client.put("/contato").status_code == 405


# ---------------------------------------------------------------------------
# Robo e abuso
# ---------------------------------------------------------------------------


def test_campo_armadilha_preenchido_nao_grava_e_nao_denuncia(client, envio_valido):
    """A resposta e IDENTICA a de um envio valido, de proposito."""
    envio_valido[CAMPO_ARMADILHA] = "robo"

    resposta = client.post("/contato", data=envio_valido)

    assert resposta.status_code == 303
    assert resposta["Location"] == "/contato/recebido"
    assert Contato.objects.count() == 0


def test_limite_por_origem_de_rede_responde_429(client, envio_valido):
    for indice in range(5):
        envio_valido["email"] = f"pessoa{indice}@exemplo.com.br"
        assert client.post("/contato", data=envio_valido).status_code == 303

    envio_valido["email"] = "excedente@exemplo.com.br"
    resposta = client.post("/contato", data=envio_valido)

    assert resposta.status_code == 429
    assert Contato.objects.count() == 5


def test_limite_conta_apenas_a_janela_configurada(client, envio_valido, settings):
    settings.CONTATO_MAX_POR_JANELA = 1
    assert client.post("/contato", data=envio_valido).status_code == 303
    assert client.post("/contato", data=envio_valido).status_code == 429

    settings.CONTATO_MAX_POR_JANELA = 3
    assert client.post("/contato", data=envio_valido).status_code == 303


# ---------------------------------------------------------------------------
# Validacao
# ---------------------------------------------------------------------------


def test_sem_consentimento_nao_grava_e_a_pagina_volta_com_o_erro(client, envio_valido):
    del envio_valido["consentimento"]

    resposta = client.post("/contato", data=envio_valido)
    corpo = resposta.content.decode("utf-8")

    assert resposta.status_code == 400
    assert "aviso de privacidade para enviar" in corpo
    assert Contato.objects.count() == 0


def test_o_que_foi_digitado_volta_preenchido_apos_erro(client, envio_valido):
    """Reprovar o envio e apagar o formulario e cobrar duas vezes pelo mesmo erro."""
    del envio_valido["consentimento"]

    corpo = client.post("/contato", data=envio_valido).content.decode("utf-8")

    assert "Maria Souza" in corpo
    assert "maria@exemplo.com.br" in corpo
    assert "portaria remota para 2 torres" in corpo


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nome", ""),
        ("email", "nao-e-email"),
        ("telefone", "sem digitos"),
    ],
)
def test_campo_invalido_reprova_o_envio(client, envio_valido, campo, valor):
    envio_valido[campo] = valor

    resposta = client.post("/contato", data=envio_valido)

    assert resposta.status_code == 400
    assert Contato.objects.count() == 0


def test_solucao_fora_do_catalogo_e_recusada(client, envio_valido):
    envio_valido["solucoes"] = ["portaria", "helicoptero"]

    assert client.post("/contato", data=envio_valido).status_code == 400
    assert Contato.objects.count() == 0


def test_mensagem_acima_do_teto_e_recusada(client, envio_valido, settings):
    settings.CONTATO_TAMANHO_MAXIMO_MENSAGEM = 50
    envio_valido["mensagem"] = "a" * 51

    assert client.post("/contato", data=envio_valido).status_code == 400
    assert Contato.objects.count() == 0
