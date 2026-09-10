"""Cadastro e edicao de conta pela tela de contas.

O projeto nao instala `django.contrib.admin` (ver `portal/settings.py`), e ate
a ADR 0005 conta se criava por `manage.py createsuperuser` no servidor. Com
quatro pessoas que entram e eventualmente mudam, isso virou SSH para cada
ajuste -- entao existe esta tela, restrita a quem administra (`is_staff`).

A senha passa pelos validadores de `AUTH_PASSWORD_VALIDATORS` (minimo 12,
nao-so-numeros, nao-comum, nao-parecida-com-os-dados-da-conta). Nao ha e-mail
configurado, entao a senha e definida aqui e comunicada por fora -- e por isso
a de criacao e obrigatoria e a de edicao e opcional ("em branco = manter").
"""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    password_validators_help_texts,
    validate_password,
)

Conta = get_user_model()

ROTULO_IS_STAFF = "Administra o portal (mexe em contas e no atendimento)"
AJUDA_IS_STAFF = (
    "Pode criar e editar contas e ver o atendimento. Deixe desmarcado para "
    "quem só usa as tarefas."
)


class _ContaFormBase(forms.ModelForm):
    def _valida_senha(self, campo: str) -> None:
        senha = self.cleaned_data.get(campo)
        if senha:
            try:
                validate_password(senha, self.instance)
            except forms.ValidationError as erro:
                self.add_error(campo, erro)


class NovaContaForm(_ContaFormBase):
    senha = forms.CharField(
        label="senha",
        widget=forms.PasswordInput,
        help_text=" ".join(password_validators_help_texts()),
        error_messages={"required": "Defina uma senha para a conta."},
    )

    class Meta:
        model = Conta
        fields = ["username", "first_name", "last_name", "is_staff"]
        labels = {
            "username": "usuário (login)",
            "first_name": "nome",
            "last_name": "sobrenome",
            "is_staff": ROTULO_IS_STAFF,
        }
        help_texts = {"is_staff": AJUDA_IS_STAFF}

    def _post_clean(self) -> None:
        super()._post_clean()
        self._valida_senha("senha")

    def save(self, commit: bool = True):
        conta = super().save(commit=False)
        conta.set_password(self.cleaned_data["senha"])
        conta.is_active = True
        if commit:
            conta.save()
        return conta


class EditarContaForm(_ContaFormBase):
    nova_senha = forms.CharField(
        label="nova senha",
        required=False,
        widget=forms.PasswordInput,
        help_text="Deixe em branco para manter a senha atual.",
    )

    class Meta:
        model = Conta
        fields = [
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "recebe_novos_contatos",
        ]
        labels = {
            "first_name": "nome",
            "last_name": "sobrenome",
            "is_staff": ROTULO_IS_STAFF,
            "is_active": "conta ativa",
            "recebe_novos_contatos": "Caixa de entrada do atendimento",
        }
        help_texts = {
            "is_staff": AJUDA_IS_STAFF,
            "is_active": (
                "Desmarcar tira o acesso sem apagar nada: o histórico de "
                "tarefas continua, mas a pessoa não entra nem recebe tarefa nova."
            ),
            "recebe_novos_contatos": (
                "Toda solicitação nova do formulário do site cai para esta "
                "pessoa. No máximo uma conta -- marcar aqui desmarca a anterior."
            ),
        }

    def clean(self):
        dados = super().clean()
        if dados.get("recebe_novos_contatos") and not dados.get("is_staff"):
            self.add_error(
                "recebe_novos_contatos",
                "Só uma conta que administra pode ser a caixa do atendimento.",
            )
        return dados

    def _post_clean(self) -> None:
        super()._post_clean()
        self._valida_senha("nova_senha")

    def save(self, commit: bool = True):
        conta = super().save(commit=False)
        if self.cleaned_data.get("nova_senha"):
            conta.set_password(self.cleaned_data["nova_senha"])
        if commit:
            conta.save()
            if conta.recebe_novos_contatos:
                # No maximo uma caixa de entrada: marcar esta desmarca as outras.
                Conta.objects.exclude(pk=conta.pk).filter(
                    recebe_novos_contatos=True
                ).update(recebe_novos_contatos=False)
        return conta
