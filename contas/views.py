"""Para onde cada conta vai depois de entrar, e o CRUD de contas.

`apos_login`: DESTINO DERIVADO, e nao fixo. Hoje todas as contas do circulo vao
para o mesmo lugar -- as tarefas, o espaco compartilhado da ADR 0005. A decisao
registrada e que havera uma area de cliente externo separada (ver
`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`); esta view e a emenda
por onde ela entra: no dia em que `/painel/cliente/` existir, muda-se esta
funcao e nenhuma navegacao precisa ser reescrita.

CRUD de contas: restrito a `is_staff` (ver `core/autorizacao.py`). Existe porque
o projeto nao instala `django.contrib.admin` e conta se criava por SSH -- ver
`contas/forms.py`. Nao ha exclusao: conta que sai perde `is_active`, e o
historico de tarefas (FK `PROTECT`) continua de pe.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from contas.forms import EditarContaForm, NovaContaForm
from core.autorizacao import somente_equipe
from tarefas.models import SITUACOES_ABERTAS

logger = logging.getLogger("portal.contas")

Conta = get_user_model()


@login_required
def apos_login(request: HttpRequest) -> HttpResponse:
    """Encaminha para a area da conta que entrou.

    Um destino so por enquanto: as tarefas. Quando a area do cliente externo
    existir, a ramificacao por conta entra aqui -- e nao num `if` espalhado por
    templates.
    """
    return HttpResponseRedirect(reverse("tarefas_lista"))


def _contexto_padrao(**extra) -> dict:
    return {"pagina_ativa": "contas", **extra}


@somente_equipe
def contas_lista(request: HttpRequest) -> HttpResponse:
    contas = Conta.objects.annotate(
        tarefas_abertas=Count(
            "tarefas", filter=Q(tarefas__situacao__in=SITUACOES_ABERTAS)
        )
    ).order_by("-is_active", "first_name", "username")
    return render(
        request,
        "contas/lista.html",
        _contexto_padrao(
            titulo="Contas — MP Soluções Corporativas",
            contas=contas,
        ),
    )


@somente_equipe
@require_http_methods(["GET", "POST"])
def conta_nova(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        formulario = NovaContaForm(request.POST)
        if formulario.is_valid():
            conta = formulario.save()
            logger.info(
                "conta criada login=%s is_staff=%s por=%s",
                conta.get_username(),
                conta.is_staff,
                request.user.get_username(),
            )
            return HttpResponseRedirect(reverse("contas_lista"))
    else:
        formulario = NovaContaForm()

    return render(
        request,
        "contas/formulario.html",
        _contexto_padrao(
            titulo="Nova conta — MP Soluções Corporativas",
            formulario=formulario,
            acao=reverse("conta_nova"),
            cabecalho="Nova conta",
            rotulo_do_botao="Criar conta",
        ),
    )


@somente_equipe
@require_http_methods(["GET", "POST"])
def conta_editar(request: HttpRequest, pk: int) -> HttpResponse:
    conta = get_object_or_404(Conta, pk=pk)
    e_a_propria = conta.pk == request.user.pk

    if request.method == "POST":
        formulario = EditarContaForm(request.POST, instance=conta)
        if formulario.is_valid():
            # Trava de nao-se-trancar-para-fora: quem edita a propria conta nao
            # pode remover o proprio acesso nem o proprio `is_staff` -- seria um
            # portal sem ninguem que administra contas.
            if e_a_propria and not formulario.cleaned_data["is_active"]:
                formulario.add_error("is_active", "Você não pode desativar a própria conta.")
            if e_a_propria and not formulario.cleaned_data["is_staff"]:
                formulario.add_error("is_staff", "Você não pode remover o próprio acesso de administração.")
            if formulario.is_valid():
                formulario.save()
                logger.info(
                    "conta editada login=%s por=%s",
                    conta.get_username(),
                    request.user.get_username(),
                )
                return HttpResponseRedirect(reverse("contas_lista"))
    else:
        formulario = EditarContaForm(instance=conta)

    return render(
        request,
        "contas/formulario.html",
        _contexto_padrao(
            titulo=f"{conta.get_username()} — MP Soluções Corporativas",
            formulario=formulario,
            acao=reverse("conta_editar", args=[conta.pk]),
            cabecalho=f"Editar {conta.get_full_name() or conta.get_username()}",
            rotulo_do_botao="Salvar alterações",
            conta=conta,
            e_a_propria=e_a_propria,
        ),
    )
