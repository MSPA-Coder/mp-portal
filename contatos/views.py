"""A pagina de contato (publica) e a area de atendimento (autenticada).

`/contato` responde GET e POST na MESMA rota: a pagina institucional mostra o
formulario, e ele envia para si mesma. Isso passou a ser possivel quando o site
foi incorporado ao portal -- antes o formulario morava num site estatico de
outra origem, e a rota precisava de lista de origens e CORS no lugar do CSRF.
O gatilho estava escrito no ADR 0001 e disparou; hoje o CSRF do Django protege
esta rota como protege qualquer outra.

O que continua valendo do desenho anterior: campo-armadilha, limite por resumo
de endereco de rede, corpo pequeno e consentimento como restricao de banco.
"""

from __future__ import annotations

import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from contatos import privacidade as aviso
from contatos.forms import CAMPO_ARMADILHA, ContatoForm
from contatos.limites import endereco_de_origem, excedeu_limite, resumo_de_endereco
from contatos.models import Contato, Segmento, Situacao, Solucao
from institucional.paginas import POR_NOME
from institucional.views import contexto_da_pagina

logger = logging.getLogger("portal.contatos")


# ---------------------------------------------------------------------------
# Pagina publica de contato
# ---------------------------------------------------------------------------


def _contexto_do_formulario(formulario: ContatoForm, **extra) -> dict:
    pagina = POR_NOME["contato"]
    marcadas: list[str] = []
    if formulario.is_bound:
        marcadas = formulario.data.getlist("solucoes")
    return {
        **contexto_da_pagina(pagina),
        "formulario": formulario,
        "segmentos": Segmento.choices,
        "solucoes": Solucao.choices,
        "solucoes_marcadas": marcadas,
        **extra,
    }


def _pagina_de_contato(
    request: HttpRequest, formulario: ContatoForm, *, status: int = 200, **extra
) -> HttpResponse:
    return render(
        request,
        POR_NOME["contato"].template,
        _contexto_do_formulario(formulario, **extra),
        status=status,
    )


def _redirecionar_para_confirmacao() -> HttpResponse:
    resposta = HttpResponseRedirect(reverse("contato_recebido"))
    # 303 e nao 302: depois de um POST o navegador deve seguir com GET, e e o
    # que evita reenviar a solicitacao ao atualizar a pagina.
    resposta.status_code = 303
    return resposta


@require_http_methods(["GET", "POST"])
def contato(request: HttpRequest) -> HttpResponse:
    """Mostra o formulario e recebe o envio.

    Ordem deliberada no POST: armadilha, limite, validacao. Cada etapa e mais
    cara que a anterior, e a mais barata recusa o trafego que nem deveria ter
    chegado.
    """
    if request.method == "GET":
        return _pagina_de_contato(request, ContatoForm())

    if (request.POST.get(CAMPO_ARMADILHA) or "").strip():
        # Resposta IDENTICA a de sucesso, e nada gravado: denunciar a deteccao
        # so ensina o robo a acertar na proxima.
        logger.info("contato descartado motivo=armadilha")
        return _redirecionar_para_confirmacao()

    ip_hash = resumo_de_endereco(endereco_de_origem(request))
    if excedeu_limite(ip_hash):
        logger.warning("contato recusado motivo=limite")
        return _pagina_de_contato(
            request, ContatoForm(request.POST), status=429, limite_excedido=True
        )

    formulario = ContatoForm(request.POST)
    if not formulario.is_valid():
        return _pagina_de_contato(request, formulario, status=400)

    agora = timezone.now()
    with transaction.atomic():
        registro = Contato.objects.create(
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
            origem=request.headers.get("Origin", "")[:200],
            ip_hash=ip_hash,
        )

    # Sem nome, e-mail ou telefone no log: ele vai para arquivo e para o console
    # do conteiner, e nao e lugar de dado pessoal.
    logger.info("contato recebido protocolo=%s", registro.protocolo)
    return _redirecionar_para_confirmacao()


def recebido(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "contatos/recebido.html",
        {"titulo": "Solicitação recebida — MP Soluções Corporativas"},
    )


def privacidade(request: HttpRequest) -> HttpResponse:
    """O aviso de privacidade, montado a partir de `contatos/privacidade.py`."""
    return render(
        request,
        "contatos/privacidade.html",
        {
            "titulo": "Aviso de privacidade — MP Soluções Corporativas",
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
    registros = Contato.objects.all()
    if filtro in Situacao.values:
        registros = registros.filter(situacao=filtro)

    paginador = Paginator(registros, 25)
    pagina = paginador.get_page(request.GET.get("pagina"))
    return render(
        request,
        "contatos/lista.html",
        {
            "titulo": "Atendimento — MP Soluções Corporativas",
            "pagina_ativa": "atendimento",
            "pagina": pagina,
            "situacoes": Situacao.choices,
            "filtro": filtro,
            "total": paginador.count,
        },
    )


@somente_atendimento
def atendimento_detalhe(request: HttpRequest, pk: int) -> HttpResponse:
    registro = get_object_or_404(Contato, pk=pk)
    return render(
        request,
        "contatos/detalhe.html",
        {
            "titulo": f"{registro.protocolo} — MP Soluções Corporativas",
            "pagina_ativa": "atendimento",
            "contato": registro,
            "situacoes": Situacao.choices,
        },
    )


@somente_atendimento
@require_POST
def atendimento_situacao(request: HttpRequest, pk: int) -> HttpResponse:
    registro = get_object_or_404(Contato, pk=pk)
    nova = request.POST.get("situacao", "")
    if nova not in Situacao.values:
        raise PermissionDenied("Situacao desconhecida.")
    registro.situacao = nova
    registro.save(update_fields=["situacao", "atualizado_em"])
    logger.info(
        "contato triado protocolo=%s situacao=%s por=%s",
        registro.protocolo,
        nova,
        request.user.get_username(),
    )
    return HttpResponseRedirect(reverse("atendimento_detalhe", args=[registro.pk]))


@somente_atendimento
@require_POST
def atendimento_excluir(request: HttpRequest, pk: int) -> HttpResponse:
    """Exclusao definitiva, a pedido do titular (LGPD, art. 18, VI).

    O protocolo fica no log e o resto some. E o unico registro que sobra do
    tratamento, e ele nao identifica ninguem.
    """
    registro = get_object_or_404(Contato, pk=pk)
    protocolo = registro.protocolo
    registro.delete()
    logger.info("contato excluido protocolo=%s por=%s", protocolo, request.user.get_username())
    return HttpResponseRedirect(reverse("atendimento_lista"))
