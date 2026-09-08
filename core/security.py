"""Cabecalhos de seguranca aplicados a toda resposta HTTP.

A Content Security Policy e estrita: nenhum script ou estilo inline, apenas
origem propria. O portal nao depende de CDN externo nem de fonte remota -- o
CSS e servido por `django.contrib.staticfiles`/WhiteNoise --, entao
``default-src 'self'`` cobre todos os assets legitimos.

A politica e os valores dos cabecalhos vem de `sharedauth.security`, o mesmo
lugar que os aplicativos irmaos usam. A biblioteca GUARDA os valores; quem
APLICA e o middleware abaixo. Esse contrato existe porque o nucleo do pacote e
Python puro e nao pode depender de Django -- pos um middleware Django dentro da
biblioteca arrastaria o framework para dentro dela.

NOTA sobre `Vary`: o ControleBancario declara `Vary: HX-Request, HX-Target`
porque uma tela e o fragmento que a atualiza compartilham a URL. Este projeto
nao usa HTMX e nenhuma URL daqui responde corpos diferentes conforme cabecalho
de apresentacao, entao a tupla nao se aplica. A rota de contato varia por
`Origin`, e quem declara isso e a propria view, na resposta em que o cabecalho
de CORS aparece.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from sharedauth.security import SECURITY_HEADERS, montar_csp

__all__ = [
    "CONTENT_SECURITY_POLICY",
    "SECURITY_HEADERS",
    "ContentSecurityPolicyMiddleware",
]

# `img-src` abre para `data:`, e este e o motivo escrito que a biblioteca exige
# no ponto da chamada: o `site.css` herdado do site institucional pinta a
# textura de ruido do rodape com um SVG embutido como URI `data:`. E a UNICA
# ocorrencia -- ha teste que reprova o aparecimento de uma segunda em outra
# diretiva. As fontes sao arquivos `woff2` servidos de `static/`, entao
# `font-src 'self'` continua fechado.
CONTENT_SECURITY_POLICY = montar_csp(imagens_data_uri=True)


class ContentSecurityPolicyMiddleware:
    """Define ``Content-Security-Policy`` e os defensivos em toda resposta.

    Middleware simples, sem dependencia nova, porque a politica e fixa para a
    aplicacao inteira: nao ha nonce, e nao ha por que haver -- nenhuma tela
    embute estilo ou script.

    `setdefault` e deliberado: o Django ja emite alguns destes cabecalhos por
    configuracao (`SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`,
    `SECURE_REFERRER_POLICY`). Os valores coincidem, e ha teste que reprova se
    um dia deixarem de coincidir.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        for header, value in SECURITY_HEADERS.items():
            response.setdefault(header, value)
        return response
