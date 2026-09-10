"""O site institucional, agora servido pela aplicacao.

Estas asercoes sao a traducao das que a CI do repositorio `MpSolucoes` fazia
por `curl` contra o nginx. Elas continuam existindo pelo mesmo motivo: as sete
paginas sao o que o cliente ve antes de decidir se liga, e uma delas quebrada e
uma venda perdida em silencio.
"""

from __future__ import annotations

import pytest
from django.utils.html import escape

from institucional.paginas import PAGINAS, POR_NOME

pytestmark = pytest.mark.django_db

CAMINHOS = [pagina.caminho for pagina in PAGINAS]


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_as_sete_paginas_respondem_sem_autenticacao(client, caminho):
    resposta = client.get(caminho)

    assert resposta.status_code == 200


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_toda_pagina_traz_cabecalho_e_rodape(client, caminho):
    """Enquanto o site era estatico, a casca vinha do SSI do nginx.

    Bastava `ssi on` sumir para as sete rotas responderem 200 sem menu e sem
    rodape -- 200 numa pagina quebrada. A asercao mudou de forma junto com o
    mecanismo, mas cobre a mesma falha.
    """
    corpo = client.get(caminho).content.decode("utf-8")

    assert 'id="siteHeader"' in corpo
    assert "<footer" in corpo
    assert 'class="mnav"' in corpo


@pytest.mark.parametrize("pagina", PAGINAS, ids=[p.nome for p in PAGINAS])
def test_cada_pagina_marca_o_proprio_item_no_menu(client, pagina):
    corpo = client.get(pagina.caminho).content.decode("utf-8")

    assert corpo.count('aria-current="page"') == 1
    assert f'href="{pagina.caminho}" class="active"' in corpo


@pytest.mark.parametrize("pagina", PAGINAS, ids=[p.nome for p in PAGINAS])
def test_cada_pagina_declara_titulo_e_descricao_proprios(client, pagina):
    corpo = client.get(pagina.caminho).content.decode("utf-8")

    assert f"<title>{escape(pagina.titulo)}</title>" in corpo
    # Comparacao com o texto escapado: o titulo de Parceiros tem "&", que sai
    # como "&amp;" no HTML.
    assert escape(pagina.descricao) in corpo


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_pagina_institucional_nao_consulta_o_banco(
    client, django_assert_num_queries, caminho
):
    """O que reduz o custo de o site ter passado a depender da aplicacao.

    Incorporar o site ao portal fez o institucional deixar de ser imune a
    defeito da aplicacao (ADR 0003). O que sobra de protecao e o conteudo
    publico continuar servivel com o PostgreSQL fora do ar -- e isso so vale
    enquanto NENHUMA destas rotas abrir consulta. Uma consulta acrescentada sem
    querer (um contador de visitas, um banner vindo do banco) apaga a garantia
    em silencio; este teste faz barulho.
    """
    with django_assert_num_queries(0):
        client.get(caminho)


def test_o_dominio_nao_esta_escrito_em_lugar_nenhum(client, settings):
    """Propriedade conquistada na fase F5 e preservada pela incorporacao.

    `canonical` e `og:url` saem do proprio request. Trocar de dominio continua
    sendo zero edicao no repositorio -- e o gatilho do L19 e justamente o
    dominio proprio entrar.
    """
    settings.ALLOWED_HOSTS = ["exemplo.invalid"]
    resposta = client.get("/solucoes", headers={"host": "exemplo.invalid"})
    corpo = resposta.content.decode("utf-8")

    assert '<link rel="canonical" href="http://exemplo.invalid/solucoes">' in corpo
    assert '<meta property="og:url" content="http://exemplo.invalid/solucoes">' in corpo


@pytest.mark.parametrize(
    "pagina", [p for p in PAGINAS if p.rota], ids=[p.nome for p in PAGINAS if p.rota]
)
def test_a_forma_com_html_redireciona_para_a_url_limpa(client, pagina):
    """Elas existiam quando o site era estatico; sumir depois de indexadas custa posicao."""
    resposta = client.get(f"/{pagina.rota}.html")

    assert resposta.status_code == 301
    assert resposta["Location"] == pagina.caminho


def test_index_html_leva_a_raiz(client):
    resposta = client.get("/index.html")

    assert resposta.status_code == 301
    assert resposta["Location"] == "/"


def test_sitemap_lista_exatamente_as_paginas_da_tabela(client, settings):
    """Enquanto era arquivo estatico, a lista era digitada a mao e podia divergir."""
    settings.ALLOWED_HOSTS = ["exemplo.invalid"]
    corpo = client.get("/sitemap.xml", headers={"host": "exemplo.invalid"}).content.decode("utf-8")

    for pagina in PAGINAS:
        assert f"<loc>http://exemplo.invalid{pagina.caminho}</loc>" in corpo
    assert corpo.count("<loc>") == len(PAGINAS)


def test_robots_aponta_o_sitemap_e_fecha_a_area_autenticada(client, settings):
    settings.ALLOWED_HOSTS = ["exemplo.invalid"]
    corpo = client.get("/robots.txt", headers={"host": "exemplo.invalid"}).content.decode("utf-8")

    assert "Sitemap: http://exemplo.invalid/sitemap.xml" in corpo
    assert "Disallow: /atendimento/" in corpo
    # Toda area sob sessao fica fora do rastreamento, e nao so a primeira que
    # existiu: para o robo, cada visita vira um desvio para o login.
    assert "Disallow: /tarefas/" in corpo


def trecho(corpo: str, inicio: str, fim: str = "</nav>") -> str:
    """Recorta um pedaco do HTML, para asserir DENTRO dele e nao na pagina toda."""
    comeco = corpo.index(inicio)
    return corpo[comeco : corpo.index(fim, comeco)]


def test_o_menu_leva_a_area_autenticada_nos_dois_menus(client):
    """O link que o visitante clica para entrar -- e que pede login.

    A asercao olha CADA menu separadamente, e nao a pagina inteira. A primeira
    versao deste teste procurava o link no corpo todo e passava com ele
    removido do menu principal, porque o menu mobile ainda o continha --
    descoberto por mutacao, que e exatamente para isso que ela serve.

    O DESTINO mudou de `/atendimento/` para `/login` quando o rotulo passou a
    ser "Login": antes, o visitante clicava no nome de uma sala em que nao
    podia entrar e era devolvido ao login por um desvio. O que este teste
    protege continua sendo o mesmo -- que exista, nos dois menus, o caminho de
    entrada.
    """
    corpo = client.get("/").content.decode("utf-8")

    principal = trecho(corpo, 'class="nav-links"')
    mobile = trecho(corpo, 'class="mnav"')

    assert 'href="/login"' in principal
    assert 'href="/login"' in mobile


def test_o_rodape_leva_ao_aviso_de_privacidade(client):
    """Era `href="#"` no site estatico. A LGPD exige que o aviso seja acessivel."""
    corpo = client.get("/").content.decode("utf-8")

    assert 'href="/privacidade"' in corpo


def test_nenhuma_pagina_depende_de_host_externo(client):
    """Fontes e imagens sao vendorizadas; a CI do site estatico ja exigia isso."""
    proibidos = ("cdn.", "fonts.googleapis", "fonts.gstatic", "//code.jquery")
    for pagina in PAGINAS:
        corpo = client.get(pagina.caminho).content.decode("utf-8")
        for host in proibidos:
            assert host not in corpo, f"{pagina.caminho} referencia {host}"


def test_o_nome_fantasia_aparece_para_quem_navega(client):
    corpo = client.get("/").content.decode("utf-8")

    assert "MP SOLUÇÕES CORPORATIVAS" in corpo
    assert '"name": "MP Soluções Corporativas"' in corpo


def test_a_pagina_de_contato_nao_esta_no_mapa_do_institucional():
    """Ela responde GET e POST, e por isso quem a serve e o app `contatos`."""
    from institucional.urls import urlpatterns

    nomes = {padrao.name for padrao in urlpatterns if padrao.name}
    assert "pagina_contato" not in nomes
    assert POR_NOME["contato"].template == "site/contato.html"
