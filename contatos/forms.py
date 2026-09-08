"""Validacao do que chega em `POST /contato`.

Formulario comum e nao `ModelForm`: os dados chegam de duas formas (campos de
formulario e corpo JSON) e passam por regras que nao sao do modelo -- o
campo-armadilha, por exemplo, nunca vira coluna. O modelo e construido pela
view depois que este formulario aprova.

O NOME DO CAMPO-ARMADILHA importa. `sobrenome` e plausivel o bastante para um
preenchedor automatico tentar, e nao existe no formulario visivel. Ele nunca e
mostrado ao visitante: quem preenche e programa, e a resposta a esse envio e
identica a de um envio valido -- e assim que se evita ensinar o robo a acertar
na proxima.
"""

from __future__ import annotations

import re

from django import forms
from django.conf import settings

from contatos.models import Segmento, Solucao

CAMPO_ARMADILHA = "sobrenome"

_DIGITOS = re.compile(r"\d")

MENSAGENS = {
    "nome": "Informe o nome de quem está pedindo contato.",
    "email": "Informe um e-mail válido para podermos responder.",
    "telefone": "Informe um telefone ou WhatsApp com DDD.",
    "consentimento": (
        "É preciso concordar com o aviso de privacidade para enviar: ele é a "
        "base legal do tratamento dos dados."
    ),
}


class ContatoForm(forms.Form):
    nome = forms.CharField(
        max_length=150,
        min_length=2,
        strip=True,
        error_messages={
            "required": MENSAGENS["nome"],
            "min_length": MENSAGENS["nome"],
        },
    )
    empresa = forms.CharField(max_length=150, required=False, strip=True)
    email = forms.EmailField(
        max_length=254,
        error_messages={
            "required": MENSAGENS["email"],
            "invalid": MENSAGENS["email"],
        },
    )
    telefone = forms.CharField(
        max_length=40,
        strip=True,
        error_messages={"required": MENSAGENS["telefone"]},
    )
    segmento = forms.ChoiceField(choices=Segmento.choices, required=False)
    solucoes = forms.MultipleChoiceField(choices=Solucao.choices, required=False)
    mensagem = forms.CharField(required=False, strip=True, widget=forms.Textarea)
    consentimento = forms.BooleanField(
        error_messages={"required": MENSAGENS["consentimento"]},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O teto vem da configuracao, entao nao pode ser declarado na classe:
        # `settings` pode mudar entre implantacoes e entre testes. Quem aplica
        # o limite e `clean_mensagem`; aqui o valor so alimenta o `maxlength`
        # do widget.
        self.fields["mensagem"].max_length = settings.CONTATO_TAMANHO_MAXIMO_MENSAGEM

    def clean_telefone(self) -> str:
        telefone = self.cleaned_data["telefone"]
        if len(_DIGITOS.findall(telefone)) < 8:
            raise forms.ValidationError(MENSAGENS["telefone"])
        return telefone

    def clean_mensagem(self) -> str:
        mensagem = self.cleaned_data.get("mensagem", "")
        teto = settings.CONTATO_TAMANHO_MAXIMO_MENSAGEM
        if len(mensagem) > teto:
            raise forms.ValidationError(
                f"A mensagem passa do limite de {teto} caracteres."
            )
        return mensagem

    def clean_solucoes(self) -> list[str]:
        # `MultipleChoiceField` ja recusa codigo desconhecido; o teto de
        # quantidade evita que alguem envie o catalogo repetido mil vezes.
        solucoes = list(dict.fromkeys(self.cleaned_data.get("solucoes", [])))
        if len(solucoes) > len(Solucao.values):
            raise forms.ValidationError("Soluções repetidas ou em excesso.")
        return solucoes
