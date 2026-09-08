"""Cumpre o prazo de retencao declarado no aviso de privacidade.

Um aviso que promete apagar em 24 meses e um sistema que nunca apaga nada e
pior do que nao ter aviso: a promessa e verificavel e esta escrita. Este
comando e o que a torna verdadeira.

Nao roda sozinho. E deliberado: enquanto o portal nao esta publicado, nao ha
agendador; quando estiver, entra como um timer systemd ao lado dos que ja
existem no repositorio `manutencao` -- e o dia de escreve-lo e o dia de decidir
com que frequencia ele roda, o que e uma decisao operacional, nao de codigo.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from contatos.models import Contato, Situacao


class Command(BaseCommand):
    help = (
        "Apaga contatos mais antigos que CONTATO_RETENCAO_DIAS, preservando os "
        "que viraram cliente."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Mostra o que seria apagado, sem apagar nada.",
        )

    def handle(self, *args, **opcoes) -> None:
        dias = settings.CONTATO_RETENCAO_DIAS
        limite = timezone.now() - timedelta(days=dias)

        # `convertido` fica de fora porque, quando a solicitacao vira contrato,
        # a base legal do tratamento deixa de ser o consentimento do formulario
        # e passa a ser a execucao do contrato -- com o prazo dele, nao com
        # este. Essa excecao esta escrita no aviso de privacidade; mudar uma
        # coisa sem a outra torna o aviso falso.
        alvo = Contato.objects.filter(criado_em__lt=limite).exclude(
            situacao=Situacao.CONVERTIDO
        )
        quantidade = alvo.count()

        if opcoes["simular"]:
            self.stdout.write(
                f"Simulacao: {quantidade} contato(s) anteriores a "
                f"{limite:%d/%m/%Y} seriam apagados (retencao de {dias} dias)."
            )
            return

        alvo.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"{quantidade} contato(s) apagados pela retencao de {dias} dias."
            )
        )
