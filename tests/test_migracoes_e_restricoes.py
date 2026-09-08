"""As garantias que so o PostgreSQL pode confirmar.

Validacao de formulario protege quem passa pelo formulario. Restricao de banco
protege tambem o `create` distraido, o comando de migracao de dados e o `psql`
aberto as tres da manha. As duas existem, e este arquivo cobre a segunda --
executando de verdade, e nao lendo o codigo-fonte.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from contatos.models import Contato
from contatos.privacidade import AVISO_VERSAO

pytestmark = pytest.mark.django_db


def base_valida(**ajustes) -> dict:
    dados = {
        "nome": "Fulano",
        "email": "fulano@exemplo.com.br",
        "telefone": "11999998888",
        "consentimento": True,
        "consentimento_em": timezone.now(),
        "aviso_versao": AVISO_VERSAO,
    }
    dados.update(ajustes)
    return dados


def test_nao_existe_contato_sem_consentimento():
    """A base legal declarada e o consentimento; sem ele, a linha nao pode existir."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Contato.objects.create(**base_valida(consentimento=False))


def test_situacao_fora_do_catalogo_e_recusada_pelo_banco():
    with pytest.raises(IntegrityError), transaction.atomic():
        Contato.objects.create(**base_valida(situacao="vendido"))


def test_registro_sem_identificacao_minima_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        Contato.objects.create(**base_valida(nome=""))

    with pytest.raises(IntegrityError), transaction.atomic():
        Contato.objects.create(**base_valida(email=""))


def test_protocolo_usa_ano_e_chave_primaria():
    contato = Contato.objects.create(**base_valida())

    assert contato.protocolo == f"MP-{contato.criado_em.year}-{contato.pk:06d}"


def test_codigo_de_solucao_desconhecido_aparece_como_esta():
    """Some da tela e o que transforma mudanca de catalogo em perda silenciosa."""
    contato = Contato.objects.create(
        **base_valida(solucoes=["portaria", "coisa_antiga"])
    )

    assert contato.solucoes_rotuladas == ["Portaria e recepção", "coisa_antiga"]


def test_nao_ha_migracao_pendente():
    """Modelo alterado sem `makemigrations` quebraria o `deploy.sh`, nao a CI."""
    try:
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
    except SystemExit:
        pytest.fail(
            "Ha alteracao de modelo sem migracao correspondente. "
            "Rode `manage.py makemigrations` e versione o arquivo gerado."
        )
