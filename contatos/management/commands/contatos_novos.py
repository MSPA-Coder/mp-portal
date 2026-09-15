"""Conta as solicitacoes novas desde um instante, para o aviso de chegada.

Quem o roda e o `aviso-contatos.timer` do repositorio `manutencao`, a cada 15
minutos, no conteiner `web` em execucao. O script do host guarda o instante
devolvido, passa-o de volta na chamada seguinte e chama o `alerta.sh` quando ha
solicitacao nova. O aviso sai do host, e nao daqui, porque o conteiner e
`read_only` e nao tem credencial de envio -- o mesmo desenho do expurgo.

A SAIDA NAO CARREGA DADO PESSOAL, de proposito: so uma contagem e um instante.
O aviso vai para o Telegram, e mandar nome, e-mail ou telefone para la seria
transferir dado de terceiro a um servico que o aviso de privacidade nao
declara. Quem recebe o aviso abre o painel para ver quem escreveu.

Formato, uma chave por linha, para o shell ler sem interpretar texto livre:

    novos=2
    ate=2026-09-15T17:32:10.123456+00:00

Sem `--desde`, a chamada so inicializa: `novos=0`, e `ate` e o agora. Assim a
primeira execucao num servidor nao avisa sobre o que ja estava na lista.
"""

from __future__ import annotations

from datetime import UTC, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone

from contatos.models import Contato, Situacao


def _instante(texto: str) -> datetime:
    try:
        instante = datetime.fromisoformat(texto)
    except ValueError as erro:
        raise CommandError(f"--desde precisa ser um instante ISO 8601: {texto!r}") from erro
    if timezone.is_naive(instante):
        raise CommandError("--desde precisa trazer o fuso horario (ex.: +00:00).")
    return instante


class Command(BaseCommand):
    help = (
        "Conta as solicitacoes em situacao Novo criadas depois de --desde. "
        "Imprime so a contagem e um instante, nunca dado pessoal."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--desde",
            help="Instante ISO 8601 com fuso, o `ate` devolvido pela chamada anterior.",
        )

    def handle(self, *args, **opcoes) -> None:
        if not opcoes["desde"]:
            self._escrever(0, timezone.now())
            return

        desde = _instante(opcoes["desde"])
        posteriores = Contato.objects.filter(criado_em__gt=desde)
        novos = posteriores.filter(situacao=Situacao.NOVO).count()
        # O instante avanca pelo pedido mais recente de QUALQUER situacao: um
        # pedido que alguem ja abriu antes do aviso nao volta a ser contado na
        # chamada seguinte.
        mais_recente = posteriores.aggregate(ultimo=Max("criado_em"))["ultimo"]
        self._escrever(novos, mais_recente or desde)

    def _escrever(self, novos: int, ate: datetime) -> None:
        self.stdout.write(f"novos={novos}")
        self.stdout.write(f"ate={ate.astimezone(UTC).isoformat()}")
