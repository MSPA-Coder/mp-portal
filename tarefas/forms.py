"""Validacao das telas de tarefa.

`ModelForm` aqui, e formulario comum em `contatos/forms.py`: la os dados vem de
fora e passam por regras que nao sao do modelo (campo-armadilha, limite por
endereco); aqui quem preenche ja esta autenticado e os campos sao exatamente as
colunas. Repetir a declaracao a mao so criaria uma segunda fonte para
`max_length`.

O responsavel e escolhido entre as contas da equipe ATIVAS. Quem saiu continua
dono das tarefas antigas -- e o historico --, mas nao aparece mais como destino
de tarefa nova.
"""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model

from tarefas.models import Andamento, Prioridade, Tarefa

MENSAGENS = {
    "titulo": "Descreva a tarefa em uma linha.",
    "responsavel": "Escolha quem fica responsável.",
    "texto": "Escreva o que aconteceu para registrar o andamento.",
}


def equipe():
    """Contas que podem receber tarefa: da equipe e em uso."""
    return get_user_model().objects.filter(is_staff=True, is_active=True).order_by(
        "first_name", "username"
    )


def nome_de_pessoa(usuario) -> str:
    """Como uma conta aparece na tela, em qualquer lugar do modulo.

    O `__str__` do modelo de usuario devolve o nome de login, que serve para
    autenticar e nao para conversar: "verifica.temp" numa lista de responsaveis
    obriga quem le a traduzir de cabeca. Aqui vem o nome, e o login so aparece
    quando nao ha nome cadastrado.
    """
    return usuario.get_full_name() or usuario.get_username()


class SelecaoDeResponsavel(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return nome_de_pessoa(obj)


class TarefaForm(forms.ModelForm):
    # Declarado a mao so por causa do rotulo de cada opcao; o `queryset` e
    # reposto no `__init__` para que uma conta criada depois da importacao do
    # modulo apareca na lista.
    responsavel = SelecaoDeResponsavel(
        queryset=equipe(),
        label="responsável",
        empty_label=None,
        error_messages={"required": MENSAGENS["responsavel"]},
    )

    class Meta:
        model = Tarefa
        fields = ["titulo", "descricao", "responsavel", "prazo", "prioridade"]
        # A situacao NAO esta aqui de proposito: ela muda pela triagem do
        # detalhe, que registra quem mudou e escreve a linha do andamento. Se
        # fosse editavel neste formulario, existiriam dois caminhos para a mesma
        # coluna e so um deles deixaria rastro.
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "prazo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        error_messages = {"titulo": {"required": MENSAGENS["titulo"]}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsavel"].queryset = equipe()
        self.fields["prioridade"].choices = Prioridade.choices
        # `DateInput` com `type=date` so mostra o valor existente se ele chegar
        # no formato que o campo do navegador entende.
        self.fields["prazo"].input_formats = ["%Y-%m-%d"]

    def clean_titulo(self) -> str:
        titulo = (self.cleaned_data.get("titulo") or "").strip()
        if not titulo:
            raise forms.ValidationError(MENSAGENS["titulo"])
        return titulo


class AndamentoForm(forms.ModelForm):
    class Meta:
        model = Andamento
        fields = ["texto"]
        widgets = {
            "texto": forms.Textarea(
                attrs={"rows": 3, "placeholder": "O que avançou, o que travou…"}
            )
        }
        error_messages = {"texto": {"required": MENSAGENS["texto"]}}

    def clean_texto(self) -> str:
        texto = (self.cleaned_data.get("texto") or "").strip()
        if not texto:
            raise forms.ValidationError(MENSAGENS["texto"])
        return texto
