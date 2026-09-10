"""As telas de tarefa: lista, ficha, cadastro e acompanhamento.

Autorizacao e `somente_equipe`, a mesma do atendimento e pela mesma razao
escrita em `core/autorizacao.py`: a conta de cliente que o ADR 0002 preve
tambem sera autenticada, e "autenticado" nao pode ser o criterio.

Dentro da equipe NAO ha segunda camada de permissao -- quem entra ve e mexe em
tudo. Sao tres pessoas que ja decidem juntas o que cada uma faz; uma matriz de
permissao aqui seria estrutura sem leitor, que e o mesmo argumento do ADR 0002.
O que existe no lugar e rastro: toda mudanca de situacao vira uma linha de
andamento com autor e data.
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from core.autorizacao import somente_equipe
from tarefas.forms import AndamentoForm, TarefaForm, equipe, nome_de_pessoa
from tarefas.models import SITUACOES_ABERTAS, Andamento, Situacao, Tarefa

logger = logging.getLogger("portal.tarefas")

#: Valor de filtro que nao e uma situacao: significa "todas as que ainda pedem
#: trabalho". E o padrao da lista, e aparece escrito no seletor -- filtro padrao
#: que esconde registro sem dizer que esta escondendo e como perder tarefa.
FILTRO_ABERTAS = "abertas"


def _tarefas_ordenadas():
    """Da mais urgente para a menos, com quem nao tem prazo por ultimo.

    `nulls_last` importa: no PostgreSQL, `ORDER BY` ascendente coloca NULL no
    FIM por padrao, mas depender do padrao do banco para uma decisao de tela e
    frageil -- e no dia de um `.reverse()` a regra se inverteria em silencio.
    """
    return Tarefa.objects.select_related("responsavel").order_by(
        F("prazo").asc(nulls_last=True), "-prioridade", "-criado_em"
    )


@somente_equipe
def lista(request: HttpRequest) -> HttpResponse:
    filtro = request.GET.get("situacao") or FILTRO_ABERTAS
    de_quem = request.GET.get("responsavel") or ""

    registros = _tarefas_ordenadas()
    if filtro == FILTRO_ABERTAS:
        registros = registros.filter(situacao__in=SITUACOES_ABERTAS)
    elif filtro in Situacao.values:
        registros = registros.filter(situacao=filtro)
    # Qualquer outro valor cai em "todas": um filtro desconhecido na barra de
    # endereco nao deve virar 500 nem lista vazia sem explicacao.

    if de_quem.isdigit():
        registros = registros.filter(responsavel_id=int(de_quem))

    paginador = Paginator(registros, 25)
    pagina = paginador.get_page(request.GET.get("pagina"))

    # Um numero por pessoa, na consulta que ja e feita de qualquer forma: e o
    # "acompanhamento simples" pedido, sem virar relatorio.
    por_pessoa = (
        equipe()
        .annotate(
            abertas=Count("tarefas", filter=Q(tarefas__situacao__in=SITUACOES_ABERTAS))
        )
        .order_by("-abertas")
    )

    return render(
        request,
        "tarefas/lista.html",
        {
            "titulo": "Tarefas — MP Soluções Corporativas",
            "pagina_ativa": "tarefas",
            "pagina": pagina,
            "situacoes": Situacao.choices,
            "filtro": filtro,
            "filtro_abertas": FILTRO_ABERTAS,
            "equipe": por_pessoa,
            "de_quem": de_quem,
            "total": paginador.count,
        },
    )


@somente_equipe
@require_http_methods(["GET", "POST"])
def nova(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        formulario = TarefaForm(request.POST)
        if formulario.is_valid():
            with transaction.atomic():
                tarefa = formulario.save(commit=False)
                tarefa.criado_por = request.user
                tarefa.save()
                Andamento.objects.create(
                    tarefa=tarefa,
                    autor=request.user,
                    texto=f"Tarefa criada para {nome_de_pessoa(tarefa.responsavel)}.",
                    automatico=True,
                )
            logger.info(
                "tarefa criada id=%s por=%s", tarefa.pk, request.user.get_username()
            )
            return HttpResponseRedirect(reverse("tarefa_detalhe", args=[tarefa.pk]))
    else:
        # Tarefa nova ja nasce com quem a esta criando como responsavel: e o
        # caso mais comum numa equipe de tres, e continua trocavel no seletor.
        formulario = TarefaForm(initial={"responsavel": request.user})

    return render(
        request,
        "tarefas/formulario.html",
        {
            "titulo": "Nova tarefa — MP Soluções Corporativas",
            "pagina_ativa": "tarefas",
            "formulario": formulario,
            "acao": reverse("tarefa_nova"),
            "cabecalho": "Nova tarefa",
            "rotulo_do_botao": "Criar tarefa",
        },
    )


@somente_equipe
@require_http_methods(["GET", "POST"])
def editar(request: HttpRequest, pk: int) -> HttpResponse:
    tarefa = get_object_or_404(Tarefa, pk=pk)

    if request.method == "POST":
        anterior = tarefa.responsavel_id
        formulario = TarefaForm(request.POST, instance=tarefa)
        if formulario.is_valid():
            with transaction.atomic():
                tarefa = formulario.save()
                if tarefa.responsavel_id != anterior:
                    # A troca de dono e a mudanca que mais gera duvida depois
                    # ("desde quando isso e meu?"). Fica escrita.
                    Andamento.objects.create(
                        tarefa=tarefa,
                        autor=request.user,
                        texto=(
                            "Responsável passou a ser "
                            f"{nome_de_pessoa(tarefa.responsavel)}."
                        ),
                        automatico=True,
                    )
            logger.info(
                "tarefa editada id=%s por=%s", tarefa.pk, request.user.get_username()
            )
            return HttpResponseRedirect(reverse("tarefa_detalhe", args=[tarefa.pk]))
    else:
        formulario = TarefaForm(instance=tarefa)

    return render(
        request,
        "tarefas/formulario.html",
        {
            "titulo": "Editar tarefa — MP Soluções Corporativas",
            "pagina_ativa": "tarefas",
            "formulario": formulario,
            "acao": reverse("tarefa_editar", args=[tarefa.pk]),
            "cabecalho": "Editar tarefa",
            "rotulo_do_botao": "Salvar alterações",
            "tarefa": tarefa,
        },
    )


@somente_equipe
def detalhe(request: HttpRequest, pk: int) -> HttpResponse:
    tarefa = get_object_or_404(
        Tarefa.objects.select_related("responsavel", "criado_por"), pk=pk
    )
    return render(
        request,
        "tarefas/detalhe.html",
        {
            "titulo": f"{tarefa.titulo} — MP Soluções Corporativas",
            "pagina_ativa": "tarefas",
            "tarefa": tarefa,
            "situacoes": Situacao.choices,
            "andamentos": tarefa.andamentos.select_related("autor"),
            "formulario": AndamentoForm(),
        },
    )


@somente_equipe
@require_POST
def mudar_situacao(request: HttpRequest, pk: int) -> HttpResponse:
    tarefa = get_object_or_404(Tarefa, pk=pk)
    nova = request.POST.get("situacao", "")
    if nova not in Situacao.values:
        raise PermissionDenied("Situacao desconhecida.")

    if nova != tarefa.situacao:
        anterior = tarefa.get_situacao_display()
        with transaction.atomic():
            tarefa.aplicar_situacao(nova)
            tarefa.save(
                update_fields=["situacao", "concluida_em", "atualizado_em"]
            )
            Andamento.objects.create(
                tarefa=tarefa,
                autor=request.user,
                texto=f"Situação: {anterior} → {tarefa.get_situacao_display()}.",
                automatico=True,
            )
        logger.info(
            "tarefa situacao id=%s valor=%s por=%s",
            tarefa.pk,
            nova,
            request.user.get_username(),
        )

    return HttpResponseRedirect(reverse("tarefa_detalhe", args=[tarefa.pk]))


@somente_equipe
@require_POST
def registrar_andamento(request: HttpRequest, pk: int) -> HttpResponse:
    tarefa = get_object_or_404(
        Tarefa.objects.select_related("responsavel", "criado_por"), pk=pk
    )
    formulario = AndamentoForm(request.POST)
    if not formulario.is_valid():
        # Volta para a propria ficha com o erro, e nao para uma tela de erro: o
        # texto que a pessoa escreveu continua na tela.
        return render(
            request,
            "tarefas/detalhe.html",
            {
                "titulo": f"{tarefa.titulo} — MP Soluções Corporativas",
                "pagina_ativa": "tarefas",
                "tarefa": tarefa,
                "situacoes": Situacao.choices,
                "andamentos": tarefa.andamentos.select_related("autor"),
                "formulario": formulario,
            },
            status=400,
        )

    andamento = formulario.save(commit=False)
    andamento.tarefa = tarefa
    andamento.autor = request.user
    andamento.save()
    # `atualizado_em` e `auto_now`: salvar a tarefa faz a lista mostrar que ela
    # teve movimento hoje, mesmo sem mudanca de situacao.
    tarefa.save(update_fields=["atualizado_em"])
    logger.info(
        "tarefa andamento id=%s por=%s", tarefa.pk, request.user.get_username()
    )
    return HttpResponseRedirect(reverse("tarefa_detalhe", args=[tarefa.pk]))
