"""As paginas do site, e o que cada uma declara.

FONTE UNICA. O `<head>` monta titulo, descricao e Open Graph daqui; o menu
marca o item ativo daqui; o `sitemap.xml` lista estas rotas e nao outras. Antes
os mesmos dados viviam em tres lugares -- o `<head>` de cada arquivo, o `map`
do nginx e o sitemap escrito a mao -- e divergir era questao de tempo.

O conteudo de cada pagina fica em `templates/site/`. O DOMINIO nao aparece aqui
nem em lugar nenhum: o gerador o recebe como parametro (`--dominio`) e dele
saem `canonical`, `og:url`, o sitemap e os enderecos de e-mail.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pagina:
    """Uma pagina institucional publica."""

    rota: str
    nome: str
    template: str
    titulo: str
    descricao: str
    classe_do_corpo: str
    rotulo_no_menu: str
    imagem: str | None = None
    imagem_alt: str | None = None
    #: Falso na confirmacao de envio: sai do sitemap e leva `noindex`.
    indexavel: bool = True

    @property
    def caminho(self) -> str:
        return f"/{self.rota}" if self.rota else "/"

    @property
    def arquivo(self) -> str:
        """Nome do arquivo gerado: `/solucoes` vira `solucoes.html`."""
        return f"{self.rota}.html" if self.rota else "index.html"


#: A ordem desta lista e a ordem do menu e a do sitemap.
PAGINAS: tuple[Pagina, ...] = (
    Pagina(
        rota="",
        nome="home",
        template="site/index.html",
        titulo="MP Soluções Corporativas — Segurança, Tecnologia e Facilities",
        descricao="Protegemos pessoas, patrimônios e operações com segurança eletrônica, portaria e facilities integrados. Monitoramento 24h, controle de acesso e gestão operacional.",
        classe_do_corpo="pg-home",
        rotulo_no_menu="Início",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="solucoes",
        nome="solucoes",
        template="site/solucoes.html",
        titulo="Soluções — MP Soluções Corporativas",
        descricao="Quatro linhas de solução em uma operação integrada: segurança eletrônica, portaria e recepção, integração tecnológica e facilities. Escopo, recursos e entregáveis de cada frente.",
        classe_do_corpo="pg-solucoes",
        rotulo_no_menu="Soluções",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="metodo",
        nome="metodo",
        template="site/metodo.html",
        titulo="Método — MP Soluções Corporativas",
        descricao="Um método claro em seis etapas, da visita técnica à melhoria contínua. Cada etapa com objetivo, responsáveis e entregáveis definidos.",
        classe_do_corpo="pg-metodo",
        rotulo_no_menu="Método",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="segmentos",
        nome="segmentos",
        template="site/segmentos.html",
        titulo="Segmentos — MP Soluções Corporativas",
        descricao="Estrutura para cada tipo de operação: pessoas, tecnologia e processos combinados conforme a rotina e o nível de exigência de cada segmento.",
        classe_do_corpo="pg-segmentos",
        rotulo_no_menu="Segmentos",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="parceiros",
        nome="parceiros",
        template="site/parceiros.html",
        titulo="Parceiros & Clientes — MP Soluções Corporativas",
        descricao="Marcas líderes integradas em um único ecossistema tecnológico, e as instituições que confiam na operação da MP Soluções Corporativas todos os dias.",
        classe_do_corpo="pg-parceiros",
        rotulo_no_menu="Parceiros",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="empresa",
        nome="empresa",
        template="site/empresa.html",
        titulo="A Empresa — MP Soluções Corporativas",
        descricao="Mais de uma década implantando soluções tecnológicas de alta performance — integradora que conecta segurança, conectividade, inteligência artificial e automação.",
        classe_do_corpo="pg-empresa",
        rotulo_no_menu="Empresa",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
    Pagina(
        rota="contato",
        nome="contato",
        template="site/contato.html",
        titulo="Contato — MP Soluções Corporativas",
        descricao="Solicite uma avaliação sem compromisso. Conte sua necessidade e receba um diagnóstico inicial com a combinação certa de segurança, portaria e facilities.",
        classe_do_corpo="pg-contato",
        rotulo_no_menu="Contato",
        imagem="site/img/16aa6ddeb-e766-468d-ad01-02390b0eb5b4.webp",
        imagem_alt="Central de monitoramento da MP Soluções Corporativas",
    ),
)

#: Paginas de apoio: fora do menu. A de privacidade e publica e indexavel; a de
#: confirmacao e para onde o `enviar.php` devolve o visitante.
PAGINAS_DE_APOIO: tuple[Pagina, ...] = (
    Pagina(
        rota="privacidade",
        nome="privacidade",
        template="site/privacidade.html",
        titulo="Aviso de privacidade — MP Soluções Corporativas",
        descricao="Como a MP Soluções Corporativas trata os dados enviados pelo formulário de contato do site, nos termos da LGPD.",
        classe_do_corpo="pg-privacidade",
        rotulo_no_menu="Privacidade",
    ),
    Pagina(
        rota="contato-enviado",
        nome="contato_enviado",
        template="site/contato_enviado.html",
        titulo="Solicitação recebida — MP Soluções Corporativas",
        descricao="Recebemos a sua solicitação de contato.",
        classe_do_corpo="pg-contato",
        rotulo_no_menu="Contato",
        indexavel=False,
    ),
    # Molde do erro: o `enviar.php` troca o marcador `<!--MENSAGEM-->` pelo
    # motivo e devolve a pagina. Fica publicada, mas fora do sitemap.
    Pagina(
        rota="contato-erro",
        nome="contato_erro",
        template="site/contato_erro.html",
        titulo="Não foi possível enviar — MP Soluções Corporativas",
        descricao="A solicitação de contato não foi enviada.",
        classe_do_corpo="pg-contato",
        rotulo_no_menu="Contato",
        indexavel=False,
    ),
)

#: Indice por nome, para o menu marcar o item ativo.
POR_NOME: dict[str, Pagina] = {pagina.nome: pagina for pagina in (*PAGINAS, *PAGINAS_DE_APOIO)}

#: O que o visitante pode escolher no formulario. Os valores sao os que o
#: `enviar.php` aceita; o rotulo e o texto exibido (e o que vai no e-mail).
SEGMENTOS: tuple[tuple[str, str], ...] = (
    ("condominios", "Condomínios"),
    ("industrias", "Indústrias"),
    ("empresas", "Empresas e escritórios"),
    ("comercio", "Comércio e varejo"),
    ("saude", "Saúde"),
    ("educacao", "Educação"),
    ("setor_publico", "Setor público"),
    ("outro", "Outro"),
)

SOLUCOES: tuple[tuple[str, str], ...] = (
    ("seguranca_eletronica", "Segurança eletrônica"),
    ("portaria", "Portaria e recepção"),
    ("facilities", "Facilities"),
    ("integradas", "Soluções integradas"),
)

#: Canais de atendimento publicados no site. O e-mail leva o dominio, que vem
#: do gerador (`contato@<dominio>`).
TELEFONE = "11 5585-3145"
WHATSAPP = "11 99580-7972"
WHATSAPP_LINK = "https://wa.me/5511995807972"
CAIXA_PUBLICA = "contato"
