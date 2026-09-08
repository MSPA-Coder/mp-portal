"""Rotas de infraestrutura do portal."""

from __future__ import annotations

from django.db import connection
from django.http import HttpRequest, JsonResponse

# O nome do servico entra na resposta e e o que o vigia do VPS procura. Nao
# mude sem mudar o monitor junto.
NOME_DO_SERVICO = "mp-portal"


def health_check(_request: HttpRequest) -> JsonResponse:
    """Responde a pergunta "o servico atende requisicao que depende do banco?".

    O `healthcheck` do Compose e o `deploy.sh` da frota usam esta rota, por isso
    a sonda executa uma consulta simples e devolve 503 quando o PostgreSQL nao
    esta disponivel. O formato da resposta segue o contrato comum aos
    aplicativos do mantenedor -- `sharedauth.health` implementa esse mesmo
    contrato para Flask, e a implementacao aqui permanece local porque este
    projeto instala somente o nucleo do pacote, sem Flask.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - qualquer falha e "nao apto"
        # 503 e nao 500: indisponibilidade temporaria e a resposta correta, e
        # nao produz traceback no log a cada sonda de 60 segundos.
        return JsonResponse({"servico": NOME_DO_SERVICO, "status": "erro"}, status=503)
    return JsonResponse({"servico": NOME_DO_SERVICO, "status": "ok"})
