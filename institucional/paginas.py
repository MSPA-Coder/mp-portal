"""As sete paginas institucionais, e o que cada uma declara.

FONTE UNICA. O `<head>` monta titulo, descricao e Open Graph daqui; o menu
marca o item ativo daqui; o `sitemap.xml` lista estas rotas e nao outras. Antes
da incorporacao ao portal, os mesmos dados viviam em tres lugares -- o `<head>`
de cada arquivo, o `map` do nginx e o sitemap escrito a mao -- e divergir era
questao de tempo.

O conteudo de cada pagina continua em `templates/site/`, migrado byte a byte do
repositorio `MpSolucoes` (fase F7, 08/09/2026). O DOMINIO nao aparece aqui nem
em lugar nenhum: `canonical`, `og:url` e o sitemap saem do proprio request, que
e a propriedade que a fase F5 conquistou e a incorporacao preserva.
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

    @property
    def caminho(self) -> str:
        return f"/{self.rota}" if self.rota else "/"


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

#: Indice por nome, para o menu marcar o item ativo.
POR_NOME: dict[str, Pagina] = {pagina.nome: pagina for pagina in PAGINAS}
