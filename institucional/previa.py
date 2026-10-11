"""Servidor local para ver a saida do gerador, so com a biblioteca padrao.

    python -m institucional.previa dist/site 5601

Imita o que o `.htaccess` faz na hospedagem: `/solucoes` serve `solucoes.html`
e a pagina 404 e a gerada. Nao executa PHP nem aplica cabecalhos de seguranca --
serve para olhar o layout, nao para validar o servidor.
"""

from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Manipulador(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        caminho = super().translate_path(path)
        alvo = Path(caminho)
        if not alvo.exists() and alvo.with_name(alvo.name + ".html").is_file():
            return str(alvo.with_name(alvo.name + ".html"))
        return caminho

    def send_error(self, code, message=None, explain=None):
        if code == 404 and (Path(self.directory) / "404.html").is_file():
            corpo = (Path(self.directory) / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(corpo)
            return
        super().send_error(code, message, explain)


def principal() -> None:
    pasta = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/site").resolve()
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 5601
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), partial(Manipulador, directory=str(pasta)))
    print(f"http://127.0.0.1:{porta}/  <-  {pasta}")
    servidor.serve_forever()


if __name__ == "__main__":
    principal()
