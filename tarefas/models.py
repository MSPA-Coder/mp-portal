"""Tarefas da equipe: o que fazer, de quem e, para quando, e como esta.

Combinado da construcao: tres pessoas, tarefa com responsavel, prazo e
situacao, e acompanhamento simples. O modelo e pequeno de proposito -- o que
existe aqui e o que uma equipe de tres pessoas de fato preenche. Campo que
ninguem preenche vira coluna vazia que todo mundo precisa ler.

O que NAO existe, e por que:

- **percentual de conclusao.** As cinco situacoes ja dizem onde a tarefa esta,
  e "70%" e uma opiniao que ninguem confere. O andamento de verdade e a linha
  do tempo abaixo.
- **exclusao.** Tarefa errada vira `CANCELADA`, e o registro fica. Apagar
  perderia o unico historico que existe de uma decisao da equipe -- diferente
  do `Contato`, onde a exclusao existe porque a LGPD da esse direito ao
  titular.
- **anexo.** O portal nao recebe upload (`FILE_UPLOAD_MAX_MEMORY_SIZE = 0`), e
  abrir essa porta e uma decisao de infraestrutura, nao de tela.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Situacao(models.TextChoices):
    A_FAZER = "a_fazer", "A fazer"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    BLOQUEADA = "bloqueada", "Bloqueada"
    CONCLUIDA = "concluida", "Concluída"
    CANCELADA = "cancelada", "Cancelada"


#: Situacoes que ainda pedem trabalho. E o filtro padrao da lista, e tambem o
#: recorte de "minhas tarefas" -- uma so definicao para os dois, porque duas
#: divergiriam no dia em que uma situacao nova aparecesse.
SITUACOES_ABERTAS: tuple[str, ...] = (
    Situacao.A_FAZER,
    Situacao.EM_ANDAMENTO,
    Situacao.BLOQUEADA,
)


class Prioridade(models.IntegerChoices):
    """Inteiro, e nao codigo de texto como `Segmento` e `Solucao`.

    Aqueles sao conjuntos nominais, onde a ordem nao significa nada e o codigo
    ASCII estavel e o que protege o registro antigo de uma mudanca de
    comunicacao. Prioridade e ordinal: o banco precisa saber que alta vem antes
    de normal, e `ORDER BY` sobre texto ordenaria "alta, baixa, normal".
    """

    BAIXA = 1, "Baixa"
    NORMAL = 2, "Normal"
    ALTA = 3, "Alta"


class Tarefa(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # `verbose_name` EXPLICITO em tudo que aparece na tela. O Django deriva o
    # rotulo do nome do atributo, e o nome do atributo e ASCII por regra da
    # casa -- sem esta linha o formulario mostra "Descricao" e "Responsavel",
    # que e a regra "acento em texto de interface, nunca em identificador"
    # falhando no lado do texto. A suite inteira passava com os rotulos errados;
    # quem viu foi o navegador.
    titulo = models.CharField(max_length=200, verbose_name="título")
    descricao = models.TextField(blank=True, verbose_name="descrição")

    # PROTECT nos dois: apagar uma conta nao pode levar junto o historico de
    # trabalho da equipe nem deixar a tarefa sem dono. Quem sair da equipe
    # perde `is_active`, e as tarefas dele sao repassadas por tela.
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tarefas",
        verbose_name="responsável",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tarefas_criadas",
        verbose_name="criada por",
    )

    prazo = models.DateField(null=True, blank=True, verbose_name="prazo")
    situacao = models.CharField(
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.A_FAZER,
        verbose_name="situação",
    )
    prioridade = models.IntegerField(
        choices=Prioridade.choices,
        default=Prioridade.NORMAL,
        verbose_name="prioridade",
    )
    concluida_em = models.DateTimeField(
        null=True, blank=True, verbose_name="concluída em"
    )

    class Meta:
        db_table = "tarefas_tarefa"
        ordering = ["-criado_em"]
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"
        indexes = [
            # "As minhas, as que ainda pedem trabalho" -- a consulta que a lista
            # faz em toda abertura.
            models.Index(fields=["responsavel", "situacao"], name="tarefa_de_quem_idx"),
            # "O que vence primeiro", dentro do que esta aberto.
            models.Index(fields=["situacao", "prazo"], name="tarefa_prazo_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(situacao__in=Situacao.values),
                name="tarefa_situacao_conhecida",
            ),
            models.CheckConstraint(
                condition=models.Q(prioridade__in=Prioridade.values),
                name="tarefa_prioridade_conhecida",
            ),
            models.CheckConstraint(
                condition=~models.Q(titulo=""),
                name="tarefa_titulo_nao_vazio",
            ),
            # A restricao que faz a data de conclusao valer alguma coisa: ela
            # existe SE E SOMENTE SE a tarefa esta concluida. Sem isso as duas
            # colunas divergem no primeiro `save(update_fields=["situacao"])`
            # distraido, e a tela passa a mostrar "Concluída" sem dizer quando
            # -- ou pior, uma data de conclusao numa tarefa reaberta.
            models.CheckConstraint(
                condition=(
                    models.Q(situacao=Situacao.CONCLUIDA, concluida_em__isnull=False)
                    | (~models.Q(situacao=Situacao.CONCLUIDA) & models.Q(concluida_em__isnull=True))
                ),
                name="tarefa_conclusao_coerente",
            ),
        ]

    def __str__(self) -> str:
        return self.titulo

    @property
    def esta_aberta(self) -> bool:
        return self.situacao in SITUACOES_ABERTAS

    @property
    def esta_atrasada(self) -> bool:
        """Prazo vencido e trabalho ainda pendente.

        Tarefa concluida ou cancelada nunca esta atrasada, mesmo que o prazo
        tenha passado: o atraso e um pedido de atencao, e pedir atencao para o
        que ja acabou e ruido que faz a marcacao inteira ser ignorada.
        """
        if self.prazo is None or not self.esta_aberta:
            return False
        return self.prazo < timezone.localdate()

    def aplicar_situacao(self, nova: str) -> None:
        """Muda a situacao e mantem `concluida_em` coerente com ela.

        Escrever as duas colunas por caminhos separados e o que a restricao
        `tarefa_conclusao_coerente` proibe; este metodo e o unico caminho, e e
        por isso que a view nao atribui `situacao` diretamente.
        """
        self.situacao = nova
        self.concluida_em = timezone.now() if nova == Situacao.CONCLUIDA else None


class Andamento(models.Model):
    """Uma linha da historia da tarefa.

    CASCADE, e nao PROTECT: um andamento nao significa nada sem a tarefa a que
    pertence. Nao ha exclusao de tarefa por tela hoje, entao na pratica isto so
    vale para um expurgo administrativo.

    `automatico` separa o que a aplicacao escreveu (mudanca de situacao) do que
    uma pessoa escreveu. Sem essa marca, a nota de alguem e o registro do
    sistema ficam com o mesmo peso na tela, e a linha do tempo perde a leitura
    rapida de "o que aconteceu" contra "o que foi dito".
    """

    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.CASCADE, related_name="andamentos"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="andamentos"
    )
    texto = models.TextField(verbose_name="andamento")
    automatico = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tarefas_andamento"
        ordering = ["-criado_em"]
        verbose_name = "andamento"
        verbose_name_plural = "andamentos"
        indexes = [
            models.Index(fields=["tarefa", "-criado_em"], name="andamento_tarefa_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(texto=""),
                name="andamento_texto_nao_vazio",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tarefa_id} - {self.criado_em:%d/%m/%Y}"
