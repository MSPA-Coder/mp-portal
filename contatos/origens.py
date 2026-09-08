"""Quem pode enviar `POST /contato`, e o que a resposta diz ao navegador.

CONTEXTO, PORQUE ESTA DECISAO PARECE ESTRANHA FORA DELE: a rota de contato e a
unica do portal que aceita POST sem sessao. O token CSRF do Django nao serve
para protege-la -- o formulario mora no site institucional, que e estatico e
pode estar em outra origem, e um token so existiria depois de uma ida e volta
para busca-lo. Mais importante: CSRF defende contra *acao executada em nome de
quem esta logado*, e aqui nao ha ninguem logado nem acao a executar em nome de
alguem.

O que efetivamente protege esta rota:

1. **lista de origens** (este modulo) -- o navegador envia `Origin` em todo
   POST, de mesma origem ou nao (Fetch Standard), e nao permite que a pagina o
   forje. Sem `Origin` conhecido, a requisicao e recusada antes de qualquer
   trabalho;
2. **limite por origem de rede** (`contatos/limites.py`);
3. **campo-armadilha** no formulario (`contatos/forms.py`);
4. **corpo pequeno** (`DATA_UPLOAD_MAX_MEMORY_SIZE` nas settings).

A lista vazia RECUSA TUDO fora do modo de depuracao. Fechar por padrao e o que
transforma "esqueci de configurar" num 403 visivel em vez de um endpoint aberto
a internet inteira.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers


def origem_da_requisicao(request: HttpRequest) -> str:
    """Devolve o cabecalho `Origin`, ou vazio quando ele nao veio."""
    return request.headers.get("Origin", "")


def origem_permitida(origem: str) -> bool:
    """Decide se aquela origem pode enviar contato.

    Comparacao exata contra a lista configurada -- nada de `endswith`, que
    aceitaria `mp-solucoes.duckdns.org.exemplo.com`.
    """
    if not origem:
        return False
    permitidas = tuple(settings.CONTATO_ORIGENS_PERMITIDAS)
    if permitidas:
        return origem in permitidas
    # Sem lista configurada: so o modo de depuracao aceita, e mesmo assim
    # apenas com `Origin` presente. Em producao isto e recusa total.
    return bool(settings.DEBUG)


def aplicar_cors(response: HttpResponse, origem: str) -> HttpResponse:
    """Acrescenta a resposta os cabecalhos que o navegador exige.

    `Access-Control-Allow-Credentials` NAO e emitido, de proposito: a rota e
    sem sessao, e liberar credencial permitiria que uma pagina de terceiro
    enviasse o cookie do portal junto. `Allow-Origin` ecoa a origem ja validada
    e nunca `*`, e por isso a resposta precisa declarar `Vary: Origin` -- sem
    isso, um cache no caminho serviria a resposta de uma origem para outra.
    """
    response["Access-Control-Allow-Origin"] = origem
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Max-Age"] = "600"
    patch_vary_headers(response, ("Origin",))
    return response
