"""Verificacoes que impedem uma implantacao publica incompleta.

O gatilho e `USE_HTTPS`, e nao `DEBUG`. O motivo e pratico: `DEBUG=False` vale
tambem no build da imagem, na suite e no Compose local, onde exigir canal do
titular ou lista de origens seria burocracia sem risco. `USE_HTTPS=True` so e
ligado quando ha um proxy TLS na frente -- ou seja, quando o servico esta
publicado e um estranho pode alcanca-lo. E ai as duas coisas deixam de ser
configuracao e passam a ser condicao para operar dentro da lei.

`manage.py check` roda antes de `migrate`, `collectstatic` e `runserver`, entao
uma implantacao mal configurada falha na subida, e nao no primeiro visitante.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error

CANAL_AUSENTE = "contatos.E001"
ORIGENS_AUSENTES = "contatos.E002"
RETENCAO_INVALIDA = "contatos.E003"


def verificar_configuracao_publica(app_configs, **kwargs) -> list[Error]:
    problemas: list[Error] = []

    if settings.CONTATO_RETENCAO_DIAS <= 0:
        problemas.append(
            Error(
                "CONTATO_RETENCAO_DIAS precisa ser positivo.",
                hint=(
                    "O aviso de privacidade declara um prazo de retencao; zero "
                    "ou negativo apagaria os contatos no mesmo dia."
                ),
                id=RETENCAO_INVALIDA,
            )
        )

    if not settings.USE_HTTPS:
        return problemas

    if not settings.CONTATO_CANAL_TITULAR:
        problemas.append(
            Error(
                "CONTATO_CANAL_TITULAR nao esta configurado.",
                hint=(
                    "O aviso de privacidade precisa dizer por onde o titular "
                    "exerce os direitos do art. 18 da LGPD. Sem esse endereco, "
                    "o aviso promete um canal que nao existe. Defina a variavel "
                    "de ambiente CONTATO_CANAL_TITULAR."
                ),
                id=CANAL_AUSENTE,
            )
        )

    if not settings.CONTATO_ORIGENS_PERMITIDAS:
        problemas.append(
            Error(
                "CONTATO_ORIGENS_PERMITIDAS esta vazia numa implantacao publica.",
                hint=(
                    "Sem lista, POST /contato recusa todo envio -- o formulario "
                    "do site responderia 403 a cada visitante. Informe a origem "
                    "do site (esquema e host, sem barra no fim)."
                ),
                id=ORIGENS_AUSENTES,
            )
        )

    return problemas
