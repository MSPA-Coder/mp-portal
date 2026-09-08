"""Recebimento do contato do site e a area de atendimento.

Sao dois publicos no mesmo modulo, e a fronteira entre eles e a unica coisa que
importa ler aqui: `receber` e publica, sem sessao e sem CSRF (ver
`contatos/origens.py` para o porque); tudo abaixo de `atendimento_` exige conta
com `is_staff` e passa pelo CSRF do Django normalmente.
"""

from __future__ import annotations

import json
import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from contatos import privacidade as aviso
from contatos.forms import CAMPO_ARMADILHA, ContatoForm
from contatos.limites import endereco_de_origem, excedeu_limite, resumo_de_endereco
from contatos.models import Contato, Situacao
from contatos.origens import aplicar_cors, origem_da_requisicao, origem_permitida

logger = logging.getLogger("portal.contatos")


# ---------------------------------------------------------------------------
# Rota publica: recebimento
# ---------------------------------------------------------------------------


def _quer_json(request: HttpRequest) -> bool:
    """Decide o formato da resposta.

    O site pode enviar por `fetch` (espera JSON) ou por submissao comum de
    formulario, que e o caminho que continua funcionando sem JavaScript. A
    diferenca esta na intencao declarada pelo cliente, nao numa configuracao.
    """
    if request.content_type == "application/json":
        return True
    return "application/json" in request.headers.get("Accept", "")


def _dados_do_corpo(request: HttpRequest):
    """Devolve (dados, erro). Aceita formulario comum e corpo JSON."""
    if request.content_type != "application/json":
        return request.POST, None
    try:
        carga = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None, "Corpo JSON invalido."
    if not isinstance(carga, dict):
        return None, "O corpo JSON precisa ser um objeto."
    # Um dicionario comum nao tem `getlist`, entao um valor unico chegaria ao
    # campo multiplo como texto -- e um texto e iteravel, o que viraria uma
    # lista de letras. Normalizar aqui evita uma mensagem de erro incompreensivel.
    if isinstance(carga.get("solucoes"), str):
        carga["solucoes"] = [carga["solucoes"]]
    return carga, None


def _resposta_de_sucesso(request: HttpRequest, protocolo: str | None) -> HttpResponse:
    """A MESMA resposta para envio valido e para envio de robo.

    `protocolo` vazio e o caso do campo-armadilha: nada foi gravado, e a
    resposta nao pode denunciar isso.
    """
    if _quer_json(request):
        corpo = {"status": "ok"}
        if protocolo:
            corpo["protocolo"] = protocolo
        return JsonResponse(corpo, status=201)
    resposta = HttpResponseRedirect(reverse("contato_recebido"))
    # 303 e nao 302: depois de um POST, o navegador deve seguir com GET. E o
    # que evita o reenvio ao atualizar a pagina de confirmacao.
    resposta.status_code = 303
    return resposta


def _resposta_de_erro(
    request: HttpRequest, *, status: int, erros: dict[str, list[str]]
) -> HttpResponse:
    if _quer_json(request):
        return JsonResponse({"status": "erro", "campos": erros}, status=status)
    return render(request, "contatos/erro.html", {"erros": erros}, status=status)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def receber(request: HttpRequest) -> HttpResponse:
    """Recebe o pedido de contato vindo do site institucional.

    Ordem deliberada: origem, depois armadilha, depois limite, depois
    validacao. Cada etapa e mais cara que a anterior, e a mais barata e a que
    recusa o trafego que nem deveria ter chegado.
    """
    origem = origem_da_requisicao(request)
    permitida = origem_permitida(origem)

    if request.method == "OPTIONS":
        # Pre-voo do CORS. Sem os cabecalhos, o navegador nem chega a enviar o
        # POST -- e o erro aparece no console dele, nao no log do servidor.
        if not permitida:
            return HttpResponse(status=403)
        return aplicar_cors(HttpResponse(status=204), origem)

    if not permitida:
        logger.warning("contato recusado motivo=origem origem=%r", origem)
        # Sem cabecalho de CORS: para o navegador a resposta ja e invisivel, e
        # para quem chamou por fora fica o 403 explicito.
        return JsonResponse({"status": "erro", "motivo": "origem"}, status=403)

    dados, erro_de_corpo = _dados_do_corpo(request)
    if erro_de_corpo is not None:
        return aplicar_cors(
            _resposta_de_erro(request, status=400, erros={"__all__": [erro_de_corpo]}),
            origem,
        )

    if (dados.get(CAMPO_ARMADILHA) or "").strip():
        logger.info("contato descartado motivo=armadilha origem=%r", origem)
        return aplicar_cors(_resposta_de_sucesso(request, protocolo=None), origem)

    ip_hash = resumo_de_endereco(endereco_de_origem(request))
    if excedeu_limite(ip_hash):
        logger.warning("contato recusado motivo=limite origem=%r", origem)
        resposta = JsonResponse({"status": "erro", "motivo": "limite"}, status=429)
        resposta["Retry-After"] = str(settings.CONTATO_JANELA_MINUTOS * 60)
        return aplicar_cors(resposta, origem)

    formulario = ContatoForm(dados)
    if not formulario.is_valid():
        return aplicar_cors(
            _resposta_de_erro(request, status=400, erros=dict(formulario.errors)),
            origem,
        )

    agora = timezone.now()
    with transaction.atomic():
        contato = Contato.objects.create(
            nome=formulario.cleaned_data["nome"],
            empresa=formulario.cleaned_data["empresa"],
            email=formulario.cleaned_data["email"],
            telefone=formulario.cleaned_data["telefone"],
            segmento=formulario.cleaned_data["segmento"],
            solucoes=formulario.cleaned_data["solucoes"],
            mensagem=formulario.cleaned_data["mensagem"],
            consentimento=True,
            consentimento_em=agora,
            aviso_versao=aviso.AVISO_VERSAO,
            origem=origem[:200],
            ip_hash=ip_hash,
        )

    # Sem nome, e-mail ou telefone no log: o log vai para arquivo e para o
    # console do conteiner, e nao e lugar de dado pessoal.
    logger.info("contato recebido protocolo=%s origem=%r", contato.protocolo, origem)
    return aplicar_cors(_resposta_de_sucesso(request, contato.protocolo), origem)


def recebido(request: HttpRequest) -> HttpResponse:
    """Confirmacao para quem enviou sem JavaScript."""
    return render(request, "contatos/recebido.html")


def privacidade(request: HttpRequest) -> HttpResponse:
    """O aviso de privacidade, montado a partir de `contatos/privacidade.py`."""
    return render(
        request,
        "contatos/privacidade.html",
        {
            "versao": aviso.AVISO_VERSAO,
            "vigente_desde": aviso.AVISO_VIGENTE_DESDE,
            "base_legal": aviso.BASE_LEGAL,
            "finalidade": aviso.FINALIDADE,
            "campos": [
                (aviso.ROTULOS_DE_CAMPO[campo], motivo)
                for campo, motivo in aviso.CAMPOS_DECLARADOS.items()
            ],
            "compartilhamento": aviso.COMPARTILHAMENTO,
            "direitos": aviso.DIREITOS_DO_TITULAR,
            "retencao_excecao": aviso.RETENCAO_EXCECAO,
            "retencao_dias": settings.CONTATO_RETENCAO_DIAS,
            "retencao_meses": settings.CONTATO_RETENCAO_DIAS // 30,
            "canal": settings.CONTATO_CANAL_TITULAR,
        },
    )


# ---------------------------------------------------------------------------
# Area de atendimento (conta com is_staff)
# ---------------------------------------------------------------------------


def somente_atendimento(view):
    """Exige sessao e `is_staff`.

    Anonimo vai para o login; autenticado sem permissao recebe 403. A diferenca
    e proposital: mandar quem ja esta logado de volta ao login sugere que a
    sessao caiu, e a pessoa tenta de novo para sempre.
    """

    @wraps(view)
    def envolvida(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return envolvida


@somente_atendimento
def atendimento_lista(request: HttpRequest) -> HttpResponse:
    filtro = request.GET.get("situacao", "")
    contatos = Contato.objects.all()
    if filtro in Situacao.values:
        contatos = contatos.filter(situacao=filtro)

    paginador = Paginator(contatos, 25)
    pagina = paginador.get_page(request.GET.get("pagina"))
    return render(
        request,
        "contatos/lista.html",
        {
            "pagina": pagina,
            "situacoes": Situacao.choices,
            "filtro": filtro,
            "total": paginador.count,
        },
    )


@somente_atendimento
def atendimento_detalhe(request: HttpRequest, pk: int) -> HttpResponse:
    contato = get_object_or_404(Contato, pk=pk)
    return render(
        request,
        "contatos/detalhe.html",
        {"contato": contato, "situacoes": Situacao.choices},
    )


@somente_atendimento
@require_POST
def atendimento_situacao(request: HttpRequest, pk: int) -> HttpResponse:
    contato = get_object_or_404(Contato, pk=pk)
    nova = request.POST.get("situacao", "")
    if nova not in Situacao.values:
        raise PermissionDenied("Situacao desconhecida.")
    contato.situacao = nova
    contato.save(update_fields=["situacao", "atualizado_em"])
    logger.info(
        "contato triado protocolo=%s situacao=%s por=%s",
        contato.protocolo,
        nova,
        request.user.get_username(),
    )
    return HttpResponseRedirect(reverse("atendimento_detalhe", args=[contato.pk]))


@somente_atendimento
@require_POST
def atendimento_excluir(request: HttpRequest, pk: int) -> HttpResponse:
    """Exclusao definitiva, a pedido do titular (LGPD, art. 18, VI).

    O protocolo fica no log e o resto some. E o unico registro que sobra do
    tratamento, e ele nao identifica ninguem.
    """
    contato = get_object_or_404(Contato, pk=pk)
    protocolo = contato.protocolo
    contato.delete()
    logger.info(
        "contato excluido protocolo=%s por=%s", protocolo, request.user.get_username()
    )
    return HttpResponseRedirect(reverse("atendimento_lista"))
