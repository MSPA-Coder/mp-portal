"""O aviso de chegada: a contagem que o host usa para avisar que ha pedido novo.

O `aviso-contatos.sh` do repositorio `manutencao` roda `contatos_novos` a cada
15 minutos e chama o `alerta.sh` quando `novos` e maior que zero. O que se prova
aqui e o contrato de que ele depende: as duas chaves, o instante que avanca sem
repetir pedido, e o que NAO pode aparecer na saida.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from contatos import privacidade as aviso
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


def criado_em(contato: Contato, instante: datetime) -> Contato:
    """`criado_em` e `auto_now_add`: so um UPDATE direto muda a data."""
    Contato.objects.filter(pk=contato.pk).update(criado_em=instante)
    contato.refresh_from_db()
    return contato


def rodar(*args: str) -> dict[str, str]:
    saida = StringIO()
    call_command("contatos_novos", *args, stdout=saida)
    return dict(linha.split("=", 1) for linha in saida.getvalue().splitlines())


@pytest.fixture
def corte() -> datetime:
    return timezone.now() - timedelta(hours=1)


def test_sem_desde_so_inicializa_e_nao_conta_o_que_ja_estava_na_lista():
    criar_contato()
    antes = timezone.now()

    resultado = rodar()

    assert resultado["novos"] == "0"
    assert datetime.fromisoformat(resultado["ate"]) >= antes


def test_conta_so_os_pedidos_novos_criados_depois_do_instante(corte):
    criado_em(criar_contato(nome="Anterior"), corte - timedelta(minutes=5))
    criado_em(criar_contato(nome="Nova 1"), corte + timedelta(minutes=5))
    criado_em(criar_contato(nome="Nova 2"), corte + timedelta(minutes=10))

    assert rodar("--desde", corte.isoformat())["novos"] == "2"


def test_pedido_ja_aberto_nao_conta_mas_avanca_o_instante(corte):
    aberto = criado_em(
        criar_contato(situacao=Situacao.EM_ATENDIMENTO), corte + timedelta(minutes=5)
    )

    resultado = rodar("--desde", corte.isoformat())

    assert resultado["novos"] == "0"
    assert datetime.fromisoformat(resultado["ate"]) == aberto.criado_em


def test_o_instante_devolvido_nao_deixa_o_mesmo_pedido_ser_avisado_duas_vezes(corte):
    criado_em(criar_contato(), corte + timedelta(minutes=5))
    ultimo = criado_em(criar_contato(), corte + timedelta(minutes=10))

    primeira = rodar("--desde", corte.isoformat())
    segunda = rodar("--desde", primeira["ate"])

    assert primeira["novos"] == "2"
    assert datetime.fromisoformat(primeira["ate"]) == ultimo.criado_em
    assert segunda == {"novos": "0", "ate": primeira["ate"]}


def test_sem_pedido_novo_o_instante_fica_onde_estava(corte):
    resultado = rodar("--desde", corte.isoformat())

    assert resultado["novos"] == "0"
    assert datetime.fromisoformat(resultado["ate"]) == corte


def test_a_saida_nao_carrega_dado_pessoal(corte):
    """O aviso vai para o Telegram; so a contagem pode sair daqui."""
    criado_em(
        criar_contato(
            nome="Maria Souza",
            empresa="Condominio Alfa",
            email="maria@exemplo.com.br",
            telefone="11988887777",
            mensagem="Portaria remota para 2 torres",
        ),
        corte + timedelta(minutes=5),
    )
    saida = StringIO()

    call_command("contatos_novos", "--desde", corte.isoformat(), stdout=saida)

    texto = saida.getvalue()
    for dado in ("Maria", "Condominio", "maria@", "11988887777", "Portaria"):
        assert dado not in texto
    assert {linha.split("=", 1)[0] for linha in texto.splitlines()} == {"novos", "ate"}


@pytest.mark.parametrize("desde", ["ontem", "2026-09-15T10:00:00"])
def test_desde_ilegivel_ou_sem_fuso_e_erro(desde):
    with pytest.raises(CommandError):
        call_command("contatos_novos", "--desde", desde, stdout=StringIO())
