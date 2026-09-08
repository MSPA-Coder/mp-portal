"""O pedido de contato vindo do site institucional.

Uma linha desta tabela e dado pessoal de terceiro. As decisoes visiveis aqui
sao consequencia disso:

- **nao existe registro sem consentimento** -- e restricao de banco, nao
  validacao de formulario, porque validacao de formulario se contorna com um
  `Contato.objects.create` distraido;
- **o endereco IP nao e guardado**, so um HMAC dele, e a chave e o
  `SECRET_KEY` da instalacao (ver `contatos/limites.py`);
- **os rotulos de segmento e solucao sao codigos ASCII estaveis**, e nao o
  texto exibido. O texto muda quando a comunicacao do site mudar; o codigo
  gravado ha dois anos precisa continuar significando a mesma coisa.
"""

from __future__ import annotations

from django.db import models


class Situacao(models.TextChoices):
    NOVO = "novo", "Novo"
    EM_ATENDIMENTO = "em_atendimento", "Em atendimento"
    CONVERTIDO = "convertido", "Convertido em cliente"
    DESCARTADO = "descartado", "Descartado"


class Segmento(models.TextChoices):
    CONDOMINIOS = "condominios", "Condomínios"
    INDUSTRIAS = "industrias", "Indústrias"
    EMPRESAS = "empresas", "Empresas e escritórios"
    COMERCIO = "comercio", "Comércio e varejo"
    SAUDE = "saude", "Saúde"
    EDUCACAO = "educacao", "Educação"
    SETOR_PUBLICO = "setor_publico", "Setor público"
    OUTRO = "outro", "Outro"


class Solucao(models.TextChoices):
    SEGURANCA_ELETRONICA = "seguranca_eletronica", "Segurança eletrônica"
    PORTARIA = "portaria", "Portaria e recepção"
    FACILITIES = "facilities", "Facilities"
    INTEGRADAS = "integradas", "Soluções integradas"


class Contato(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    nome = models.CharField(max_length=150)
    empresa = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=254)
    telefone = models.CharField(max_length=40)
    segmento = models.CharField(max_length=20, choices=Segmento.choices, blank=True)
    # Lista de codigos de `Solucao`. JSON e nao tabela de ligacao porque o
    # conjunto e fechado, pequeno e nunca e consultado por juncao -- so lido
    # junto com o registro. Uma tabela aqui seria estrutura sem leitor.
    solucoes = models.JSONField(default=list, blank=True)
    mensagem = models.TextField(blank=True)

    consentimento = models.BooleanField()
    consentimento_em = models.DateTimeField()
    aviso_versao = models.CharField(max_length=20)

    origem = models.CharField(max_length=200, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    situacao = models.CharField(
        max_length=20, choices=Situacao.choices, default=Situacao.NOVO
    )

    class Meta:
        db_table = "contatos_contato"
        ordering = ["-criado_em"]
        verbose_name = "contato"
        verbose_name_plural = "contatos"
        indexes = [
            # Consulta do limite de envios: "quantos deste resumo de IP nos
            # ultimos N minutos".
            models.Index(fields=["ip_hash", "criado_em"], name="contato_ip_janela_idx"),
            # Consulta da area de atendimento, que sempre filtra por situacao e
            # ordena do mais novo para o mais antigo.
            models.Index(fields=["situacao", "-criado_em"], name="contato_triagem_idx"),
        ]
        constraints = [
            # A restricao que da sentido ao aviso de privacidade: a base legal
            # declarada e o consentimento, entao um registro sem consentimento
            # nao pode existir -- nem por caminho que nao passe pelo formulario.
            models.CheckConstraint(
                condition=models.Q(consentimento=True),
                name="contato_exige_consentimento",
            ),
            models.CheckConstraint(
                condition=models.Q(situacao__in=Situacao.values),
                name="contato_situacao_conhecida",
            ),
            # Sem identificacao nao ha como responder, e um registro que nao
            # serve a finalidade declarada nao deveria ser guardado.
            models.CheckConstraint(
                condition=~models.Q(nome="") & ~models.Q(email=""),
                name="contato_identificacao_minima",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.protocolo} - {self.nome}"

    @property
    def protocolo(self) -> str:
        """Referencia curta que a pessoa pode citar numa conversa.

        Derivada da chave primaria e do ano; nao e guardada em coluna porque
        nao ha o que guardar -- os dois componentes ja estao na linha.
        """
        ano = self.criado_em.year if self.criado_em else 0
        return f"MP-{ano}-{self.pk:06d}"

    @property
    def solucoes_rotuladas(self) -> list[str]:
        """Os codigos gravados traduzidos para exibicao.

        Codigo desconhecido (gravado por uma versao anterior do catalogo)
        aparece como esta, em vez de sumir da tela: some da tela e o que
        transforma uma mudanca de catalogo em perda silenciosa de informacao.
        """
        rotulos = dict(Solucao.choices)
        return [rotulos.get(codigo, codigo) for codigo in self.solucoes]
