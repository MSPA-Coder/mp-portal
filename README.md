# MP Portal

O site da **MP Soluções Corporativas**: sete páginas institucionais estáticas,
mais um formulário de contato que envia a solicitação por e-mail.

O repositório é o **gerador** do site. O que vai para a hospedagem
compartilhada (Hostinger, `mp-solucoes.seg.br`) é a pasta `dist/site`, gerada
a partir dos templates de `templates/site/` — ver
`docs/adr/0006-site-estatico-na-hospedagem-compartilhada.md`.

## Gerar o site

O domínio é parâmetro e não está escrito em arquivo nenhum:

```bash
DOMINIO=mp-solucoes.seg.br docker compose run --build --rm gerar
```

Sem `COM_FORMULARIO=1` a página de contato mostra telefone, WhatsApp e e-mail.
Com ele, mostra o formulário e a saída inclui o `enviar.php`:

```bash
DOMINIO=mp-solucoes.seg.br COM_FORMULARIO=1 docker compose run --build --rm gerar
```

## Ver no navegador

```bash
python -m institucional.previa dist/site 5601
```

Serve a saída com as URLs limpas (`/solucoes`), como o `.htaccess` faz na
hospedagem. Não executa PHP.

## Páginas

| | |
|---|---|
| `/`, `/solucoes`, `/metodo`, `/segmentos`, `/parceiros`, `/empresa`, `/contato` | As sete páginas, cada uma um documento. Título, descrição, imagem e menu saem de `institucional/paginas.py`. |
| `/privacidade` | Aviso de privacidade (LGPD). |
| `/contato-enviado`, `/contato-erro` | Confirmação e molde de erro do formulário (fora do menu, do sitemap e dos buscadores). |
| `/enviar.php` | Único PHP: recebe o formulário e o encaminha por e-mail. |
| `/robots.txt`, `/sitemap.xml`, `/404.html`, `.htaccess` | Gerados. |

## Testes

```bash
docker compose run --build --rm quality
```

Roda Ruff e a suíte. O `enviar.php` tem teste próprio, num contêiner PHP:

```bash
DOMINIO=exemplo.com.br COM_FORMULARIO=1 docker compose run --rm gerar
docker run --rm -v "$PWD/php:/php:ro" -v "$PWD/dist/site:/site:ro" php:8.3-cli sh /php/testar.sh
```

Publicação, configuração do formulário, DNS e pendências: `docs/operacao.md`.
