"""Limite de envios, e o resumo de IP que o torna possivel sem guardar o IP.

DUAS COISAS QUE PARECEM UMA SO. Guardar o endereco IP de quem preenche um
formulario e coletar dado pessoal que a finalidade declarada nao pede. Nao
guardar nada torna impossivel distinguir cinco pessoas de um robo. A saida e o
resumo: um HMAC-SHA256 do endereco com o `SECRET_KEY` da instalacao, que
permite contar repeticoes e nao permite recuperar o endereco -- e que muda por
completo se a chave for trocada, o que na pratica expira a serie inteira.

O limite e verificado contra a propria tabela, sem cache: com tres processos do
gunicorn, um contador em memoria vale um terco do que promete, e a alternativa
seria acrescentar Redis a frota inteira para uma rota que recebe poucos envios
por dia. Consulta indexada por (`ip_hash`, `criado_em`).

Consequencia honesta: expurgar registros antigos (`manage.py
expurgar_contatos`) zera a janela daquele resumo. Como a janela padrao e de
minutos e a retencao e de anos, isso nunca se encontra na pratica.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone


def _dentro_de_alguma_rede(endereco: str, redes: tuple[str, ...]) -> bool:
    try:
        ip = ipaddress.ip_address(endereco)
    except ValueError:
        return False
    for rede in redes:
        try:
            if ip in ipaddress.ip_network(rede, strict=False):
                return True
        except ValueError:
            continue
    return False


def endereco_de_origem(request: HttpRequest) -> str:
    """Descobre o endereco do cliente, sem acreditar no que ele mesmo diz.

    `X-Forwarded-For` e escrito pelo cliente e reescrito por cada proxy no
    caminho. Ele so e consultado quando a conexao chega de um proxy declarado
    em `CONTATO_PROXIES_CONFIAVEIS`; ai a leitura e da DIREITA para a esquerda,
    pulando os proxies conhecidos, porque o que esta a esquerda pode ter sido
    inventado pelo cliente. Sem configuracao de proxy, vale `REMOTE_ADDR` e
    ponto -- que e o correto para a instalacao local.
    """
    remoto = request.META.get("REMOTE_ADDR", "")
    confiaveis = tuple(settings.CONTATO_PROXIES_CONFIAVEIS)
    if not confiaveis or not _dentro_de_alguma_rede(remoto, confiaveis):
        return remoto

    encadeados = [
        parte.strip()
        for parte in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
        if parte.strip()
    ]
    for candidato in reversed(encadeados):
        if not _dentro_de_alguma_rede(candidato, confiaveis):
            return candidato
    return remoto


def resumo_de_endereco(endereco: str) -> str:
    """HMAC-SHA256 do endereco, em hexadecimal. Vazio entra, vazio sai."""
    if not endereco:
        return ""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        endereco.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def excedeu_limite(ip_hash: str) -> bool:
    """Diz se aquele resumo ja enviou demais na janela configurada.

    Resumo vazio (endereco desconhecido) nao e limitado: seria o mesmo balde
    para todo mundo, e um unico robo trancaria a rota para todos os visitantes.
    """
    if not ip_hash:
        return False
    from contatos.models import Contato

    desde = timezone.now() - timedelta(minutes=settings.CONTATO_JANELA_MINUTOS)
    recentes = Contato.objects.filter(ip_hash=ip_hash, criado_em__gte=desde).count()
    return recentes >= settings.CONTATO_MAX_POR_JANELA
