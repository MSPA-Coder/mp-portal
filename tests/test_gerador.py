"""O que o gerador entrega: o site estatico que vai para o `public_html`.

Os testes geram a saida de verdade, numa pasta temporaria, e conferem
propriedades dela -- paginas, metadados, links, CSP, formulario ligado e
desligado --, e nao o texto literal de cada pagina.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import pytest
from sharedauth.security import SECURITY_HEADERS, montar_csp

from institucional import gerador
from institucional import paginas as p

DOMINIO = "exemplo.com.br"
RAIZ = Path(__file__).resolve().parent.parent
TODAS = (*p.PAGINAS, *p.PAGINAS_DE_APOIO)


@pytest.fixture(scope="module")
def sem_formulario(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("sem") / "site"
    gerador.gerar(destino, DOMINIO, com_formulario=False)
    return destino


@pytest.fixture(scope="module")
def com_formulario(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("com") / "site"
    gerador.gerar(destino, DOMINIO, com_formulario=True)
    return destino


def ler(pasta: Path, nome: str) -> str:
    return (pasta / nome).read_text(encoding="utf-8")


class Coletor(HTMLParser):
    """Junta links e recursos locais, scripts embutidos e atributos `style`."""

    def __init__(self) -> None:
        super().__init__()
        self.referencias: list[str] = []
        self.scripts_embutidos = 0
        self.estilos_embutidos = 0
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.formularios: list[dict[str, str | None]] = []
        self._em_script = False

    def handle_starttag(self, tag, atributos):
        a = dict(atributos)
        if "style" in a:
            self.estilos_embutidos += 1
        if tag == "script":
            if a.get("src"):
                self.referencias.append(a["src"])
            else:
                self._em_script = True
        if tag == "style":
            self.estilos_embutidos += 1
        if tag in {"a", "link"} and a.get("href"):
            self.referencias.append(a["href"])
        if tag in {"img", "source"} and a.get("src"):
            self.referencias.append(a["src"])
        if tag == "meta" and a.get("name"):
            self.meta[a["name"]] = a.get("content") or ""
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "form":
            self.formularios.append(a)

    def handle_data(self, dado):
        if self._em_script and dado.strip() and not dado.lstrip().startswith("{"):
            self.scripts_embutidos += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self._em_script = False


def examinar(pasta: Path, nome: str) -> Coletor:
    coletor = Coletor()
    coletor.feed(ler(pasta, nome))
    return coletor


# ---------------------------------------------------------------------------
# Paginas e metadados
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pagina", TODAS, ids=lambda pg: pg.nome)
def test_cada_pagina_da_tabela_vira_um_arquivo_com_seu_titulo(sem_formulario, pagina):
    html = ler(sem_formulario, pagina.arquivo)
    assert f"<title>{escape(pagina.titulo)}</title>" in html


@pytest.mark.parametrize("pagina", TODAS, ids=lambda pg: pg.nome)
def test_canonical_e_og_url_saem_do_dominio_informado(sem_formulario, pagina):
    coletor = examinar(sem_formulario, pagina.arquivo)
    esperado = f"https://{DOMINIO}{pagina.caminho}"
    assert coletor.canonical == esperado
    assert f'<meta property="og:url" content="{esperado}">' in ler(sem_formulario, pagina.arquivo)


def test_paginas_nao_indexaveis_levam_noindex_e_as_demais_nao(sem_formulario):
    for pagina in TODAS:
        meta = examinar(sem_formulario, pagina.arquivo).meta
        assert ("robots" in meta) is (not pagina.indexavel), pagina.nome


def test_o_menu_lista_so_as_sete_paginas_do_site(sem_formulario):
    html = ler(sem_formulario, "index.html")
    menu = re.search(r'<nav class="nav-links".*?</nav>', html, re.S).group(0)
    for pagina in p.PAGINAS:
        assert f'href="{pagina.caminho}"' in menu
    assert "/privacidade" not in menu
    assert "/login" not in html and "/painel" not in html


def test_sitemap_lista_exatamente_as_paginas_indexaveis(sem_formulario):
    locs = re.findall(r"<loc>(.*?)</loc>", ler(sem_formulario, "sitemap.xml"))
    esperado = [f"https://{DOMINIO}{pg.caminho}" for pg in TODAS if pg.indexavel]
    assert locs == esperado


def test_robots_aponta_o_sitemap_do_dominio_e_esconde_o_que_nao_indexa(sem_formulario):
    robots = ler(sem_formulario, "robots.txt")
    assert f"Sitemap: https://{DOMINIO}/sitemap.xml" in robots
    for pagina in TODAS:
        if not pagina.indexavel:
            assert f"Disallow: {pagina.caminho}" in robots


def test_o_dominio_nao_esta_escrito_em_arquivo_do_repositorio():
    # Fora da documentacao e dos testes: o dominio e parametro do gerador.
    for pasta in ("institucional", "templates", "static", "php"):
        for arquivo in (RAIZ / pasta).rglob("*"):
            if arquivo.is_file() and arquivo.suffix in {".py", ".html", ".css", ".js", ".php"}:
                assert "mp-solucoes" not in arquivo.read_text(encoding="utf-8"), arquivo


def test_dominio_invalido_e_recusado(tmp_path):
    with pytest.raises(SystemExit):
        gerador.gerar(tmp_path / "x", "nao é domínio")


# ---------------------------------------------------------------------------
# Contato publicado
# ---------------------------------------------------------------------------


def test_telefone_whatsapp_e_email_estao_publicados_sem_mascara(sem_formulario):
    for nome in ("index.html", "contato.html"):
        html = ler(sem_formulario, nome)
        assert p.TELEFONE in html
        assert f'href="{p.WHATSAPP_LINK}"' in html
        assert f'href="mailto:contato@{DOMINIO}"' in html
        assert "*****" not in html


def test_whatsapp_aponta_para_o_numero_exibido():
    digitos = re.sub(r"\D", "", p.WHATSAPP)
    assert f"https://wa.me/55{digitos}" == p.WHATSAPP_LINK


# ---------------------------------------------------------------------------
# Formulario ligado e desligado
# ---------------------------------------------------------------------------


def test_sem_formulario_a_pagina_so_oferece_os_canais(sem_formulario):
    coletor = examinar(sem_formulario, "contato.html")
    assert coletor.formularios == []
    assert not (sem_formulario / "enviar.php").exists()


def test_com_formulario_ele_envia_para_o_enviar_php(com_formulario):
    coletor = examinar(com_formulario, "contato.html")
    assert [f["action"] for f in coletor.formularios] == ["/enviar.php"]
    assert coletor.formularios[0]["method"] == "post"
    assert (com_formulario / "enviar.php").is_file()


def test_todo_campo_do_formulario_e_lido_pelo_enviar_php(com_formulario):
    html = re.search(r"<form.*?</form>", ler(com_formulario, "contato.html"), re.S).group(0)
    php = ler(com_formulario, "enviar.php")
    nomes = set(re.findall(r'name="([a-z_\[\]]+)"', html))
    assert {"nome", "email", "telefone", "consentimento", "sobrenome", "solucoes[]"} <= nomes
    for nome in nomes:
        assert f"'{nome.removesuffix('[]')}'" in php, nome


def test_enviar_php_recebe_as_listas_da_tabela_unica(com_formulario):
    php = ler(com_formulario, "enviar.php")
    assert "@@" not in php
    for valor, rotulo in (*p.SEGMENTOS, *p.SOLUCOES):
        assert f"'{valor}' => '{rotulo}'" in php


def test_as_opcoes_do_formulario_sao_as_da_tabela_unica(com_formulario):
    html = ler(com_formulario, "contato.html")
    for valor, _ in p.SEGMENTOS:
        assert f'<option value="{valor}">' in html
    for valor, _ in p.SOLUCOES:
        assert f'name="solucoes[]" value="{valor}"' in html


def test_o_molde_de_erro_tem_o_marcador_que_o_php_substitui(com_formulario):
    assert gerador.MARCADOR_DO_ERRO in ler(com_formulario, "contato-erro.html")
    assert gerador.MARCADOR_DO_ERRO in (RAIZ / "php" / "enviar.php").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# CSP e recursos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pagina", TODAS, ids=lambda pg: pg.nome)
def test_nenhuma_pagina_tem_script_nem_estilo_embutido(com_formulario, pagina):
    coletor = examinar(com_formulario, pagina.arquivo)
    assert coletor.scripts_embutidos == 0
    assert coletor.estilos_embutidos == 0


def test_nao_ha_sintaxe_de_template_vazada(com_formulario):
    for arquivo in com_formulario.glob("*.html"):
        texto = arquivo.read_text(encoding="utf-8")
        assert "{%" not in texto and "{{" not in texto and "{#" not in texto, arquivo.name


PERMITIDOS = ("https://wa.me/", "https://schema.org", "http://www.w3.org/", f"https://{DOMINIO}")


def test_nenhum_recurso_externo_alem_dos_declarados(com_formulario):
    # Recurso externo e excecao declarada: ajuste a CSP e este teste na mesma
    # mudanca, e registre o motivo -- inclusive no aviso de privacidade, se o
    # terceiro receber dado do visitante.
    achados = []
    for arquivo in (*com_formulario.glob("*.html"), *com_formulario.rglob("*.css")):
        for url in re.findall(r"https?://[^\s\"')<>]+", arquivo.read_text(encoding="utf-8")):
            if not url.startswith(PERMITIDOS):
                achados.append((arquivo.name, url))
    assert achados == []


def test_a_unica_folga_de_img_src_e_data_uri():
    assert "img-src 'self' data:" in gerador.CSP
    assert montar_csp(imagens_data_uri=True) == gerador.CSP
    assert gerador.CSP.count("data:") == 1


def test_htaccess_carrega_a_csp_e_os_cabecalhos_da_biblioteca(sem_formulario):
    regras = ler(sem_formulario, ".htaccess")
    assert f'Content-Security-Policy "{gerador.CSP}"' in regras
    for nome, valor in SECURITY_HEADERS.items():
        assert f'Header always set {nome} "{valor}"' in regras
    assert "Strict-Transport-Security" in regras


def test_htaccess_redireciona_https_e_html_e_so_deixa_passar_o_enviar_php(sem_formulario):
    regras = ler(sem_formulario, ".htaccess")
    assert "%{HTTPS} !=on" in regras
    assert "RewriteRule ^(.+)\\.html$ /$1 [R=301,L]" in regras
    assert "RewriteRule ^(.+)$ $1.html [L]" in regras
    assert "enviar\\.php" in regras and "Require all denied" in regras
    assert "Options -Indexes" in regras


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


def _existe(pasta: Path, referencia: str) -> bool:
    caminho = referencia.split("#")[0].split("?")[0]
    if caminho in {"", "/"}:
        return True
    alvo = pasta / caminho.lstrip("/")
    return (
        alvo.is_file()
        or alvo.with_name(alvo.name + ".html").is_file()
        or caminho == "/enviar.php"  # so existe com o formulario ligado
    )


@pytest.mark.parametrize("pagina", TODAS, ids=lambda pg: pg.nome)
def test_todo_link_e_recurso_local_existe_na_saida(com_formulario, pagina):
    quebrados = []
    for ref in examinar(com_formulario, pagina.arquivo).referencias:
        if ref.startswith(("http:", "https:", "mailto:", "tel:", "#")):
            continue
        if not _existe(com_formulario, ref):
            quebrados.append(ref)
    assert quebrados == []


def test_css_e_js_levam_versao_pelo_conteudo(sem_formulario):
    html = ler(sem_formulario, "index.html")
    assert re.search(r'/site/css/site\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'/site/js/site\.js\?v=[0-9a-f]{8}"', html)


def test_static_de_arquivo_inexistente_e_erro_de_build():
    from django import template

    from institucional.tags_estaticas import versao_do_arquivo

    with pytest.raises(template.TemplateSyntaxError):
        versao_do_arquivo("site/nao-existe.css")


def test_static_e_copiado_para_a_raiz(sem_formulario):
    assert (sem_formulario / "favicon.svg").is_file()
    assert (sem_formulario / "site" / "css" / "site.css").is_file()
    assert not (sem_formulario / "static").exists()


# ---------------------------------------------------------------------------
# Repositorio: LF, sem BOM
# ---------------------------------------------------------------------------


def test_arquivos_de_texto_sao_lf_sem_bom():
    sufixos = {".py", ".html", ".css", ".js", ".php", ".sh", ".toml", ".md", ".yml", ".yaml"}
    for pasta in ("institucional", "templates", "static", "php", "tests", "docs", ".github"):
        for arquivo in (RAIZ / pasta).rglob("*"):
            if arquivo.is_file() and arquivo.suffix in sufixos:
                bruto = arquivo.read_bytes()
                assert not bruto.startswith(b"\xef\xbb\xbf"), arquivo
                assert b"\r\n" not in bruto, arquivo
