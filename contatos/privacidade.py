"""O aviso de privacidade como dado, e nao so como texto de template.

A partir do momento em que o site tem formulario com destino, a MP Solucoes
passa a tratar dado pessoal de terceiro e responde como CONTROLADORA sob a Lei
13.709/2018. O achado L20 do LEVANTAMENTO_2026-09.md exige o minimo: aviso
acessivel, finalidade declarada, base legal, prazo de retencao e canal para o
titular exercer os direitos do art. 18.

O que este modulo acrescenta a esse minimo e uma amarra mecanica: as constantes
abaixo sao a fonte do texto renderizado em `/privacidade` E o que os testes
comparam com o modelo. Um campo novo em `Contato` sem linha correspondente aqui
reprova a suite -- porque o modo classico de um aviso de privacidade virar
mentira e o codigo passar a coletar algo que o texto nao menciona.

`AVISO_VERSAO` e gravado em cada registro. Isso responde, um ano depois, a
pergunta que importa: a qual texto exatamente aquela pessoa consentiu.

As CHAVES sao ASCII porque sao identificadores; os VALORES sao texto exibido a
uma pessoa e por isso levam acento, como todo texto de interface do projeto.
"""

from __future__ import annotations

from datetime import date

#: Versao do texto. Mude junto com o texto, nunca depois.
AVISO_VERSAO = "1.0"

#: Data a partir da qual esta versao vale.
AVISO_VIGENTE_DESDE = date(2026, 9, 8)

#: Base legal do tratamento. Consentimento (art. 7o, I) e nao legitimo
#: interesse: o titular preenche um formulario espontaneamente e marca a caixa,
#: entao a base mais simples e a mais defensavel e a que ele mesmo forneceu.
BASE_LEGAL = "Consentimento do titular (Lei 13.709/2018, art. 7º, inciso I)."

#: Finalidade unica. Escrever "e outras finalidades correlatas" seria o mesmo
#: que nao declarar finalidade nenhuma.
FINALIDADE = (
    "Responder à solicitação de contato ou de orçamento enviada pelo site e "
    "conduzir a tratativa comercial dela decorrente."
)

#: Cada campo persistido e por que ele existe. As chaves precisam ser
#: EXATAMENTE os campos do modelo `Contato` (fora a chave primaria) -- ha teste
#: comparando os dois conjuntos.
CAMPOS_DECLARADOS: dict[str, str] = {
    "nome": "Identificar quem pediu contato e endereçar a resposta.",
    "empresa": "Entender o contexto do pedido (condomínio, indústria, escritório).",
    "email": "Responder à solicitação.",
    "telefone": "Responder à solicitação pelo canal que costuma ser o mais rápido.",
    "segmento": "Direcionar o atendimento à linha de solução adequada.",
    "solucoes": "Saber quais serviços interessam antes do primeiro contato.",
    "mensagem": "Texto livre que o próprio titular escreveu sobre a necessidade dele.",
    "consentimento": "Registrar que houve concordância expressa com este aviso.",
    "consentimento_em": "Registrar quando a concordância foi dada.",
    "aviso_versao": "Registrar a qual versão deste texto a concordância se refere.",
    "origem": "Registrar de qual endereço de site o envio partiu, para conferir abuso.",
    "ip_hash": (
        "Impedir envio automatizado em massa. O endereço IP não é guardado: "
        "guardamos um resumo criptográfico dele, que não permite recuperar o "
        "endereço original."
    ),
    "criado_em": "Marcar o início do prazo de retenção.",
    "situacao": "Controle interno do andamento do atendimento.",
    "atualizado_em": "Controle interno da última alteração do registro.",
}

#: Como cada campo aparece no aviso. Chaves identicas as de
#: `CAMPOS_DECLARADOS` -- ha teste comparando os dois conjuntos, porque um
#: campo sem rotulo apareceria no aviso com o nome da coluna do banco.
ROTULOS_DE_CAMPO: dict[str, str] = {
    "nome": "Nome",
    "empresa": "Empresa ou condomínio",
    "email": "E-mail",
    "telefone": "Telefone ou WhatsApp",
    "segmento": "Segmento de atuação",
    "solucoes": "Soluções de interesse",
    "mensagem": "Mensagem",
    "consentimento": "Concordância com este aviso",
    "consentimento_em": "Data e hora da concordância",
    "aviso_versao": "Versão deste aviso aceita",
    "origem": "Endereço do site de onde o envio partiu",
    "ip_hash": "Resumo criptográfico do endereço de rede",
    "criado_em": "Data e hora do envio",
    "situacao": "Situação do atendimento",
    "atualizado_em": "Data e hora da última alteração",
}

#: Excecao ao prazo de retencao, aplicada por `manage.py expurgar_contatos`.
RETENCAO_EXCECAO = (
    "Se a solicitação resultar em contrato, os dados passam a ser tratados no "
    "âmbito dessa relação contratual e seguem o prazo dela, e não o prazo "
    "acima."
)

#: Com quem os dados sao compartilhados. Hoje: ninguem. Esta linha existe para
#: que acrescentar um servico de terceiro obrigue a mexer no aviso.
COMPARTILHAMENTO = (
    "Nenhum. Os dados ficam no servidor da própria MP Soluções Corporativas e não são "
    "enviados a serviço de terceiro, nem para análise, nem para envio de "
    "e-mail, nem para publicidade."
)

#: Direitos do art. 18 que o canal precisa atender.
DIREITOS_DO_TITULAR = (
    "confirmação da existência de tratamento",
    "acesso aos dados",
    "correção de dado incompleto, inexato ou desatualizado",
    "anonimização, bloqueio ou eliminação de dado desnecessário ou excessivo",
    "eliminação dos dados tratados com base no consentimento",
    "informação sobre compartilhamento",
    "revogação do consentimento",
)
