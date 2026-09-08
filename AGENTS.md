# MP Portal — orientações de trabalho

## Escopo

Aplicação Django que recebe as solicitações de contato do site institucional da
MP Soluções (repositório `MpSolucoes`) e as guarda em PostgreSQL, com área de
atendimento autenticada e aviso de privacidade. É o repositório previsto pela
fase **F7** do `LEVANTAMENTO_2026-09.md` (repositório `manutencao`).

Fontes de verdade, nesta ordem: o código, este arquivo, o `README.md`,
`docs/operacao.md`, `docs/adr/` e o repositório `manutencao` para a
infraestrutura compartilhada do VPS.

**O portal não está publicado.** Não existe vhost, subdomínio, entrada no
`deploy.sh`, backup nem monitor para ele. O que falta, e em que ordem, está em
`docs/operacao.md` — e a publicação aciona três decisões hoje adiadas
(L06, L19 e L11 da §6 do levantamento).

## Invariantes

- **Uma linha de `contatos_contato` é dado pessoal de terceiro.** Toda mudança
  no modelo passa por `contatos/privacidade.py`: o aviso declara campo a campo
  o que é guardado, e a suíte compara os dois conjuntos. Campo novo sem linha
  no aviso reprova a CI — e é assim que se evita um aviso que virou mentira.
- **Consentimento é restrição de banco**, não validação de formulário
  (`CheckConstraint contato_exige_consentimento`). A base legal declarada é o
  consentimento; registro sem ele não pode existir nem por `create` distraído.
- **O endereço IP não é guardado.** Só o HMAC dele com o `SECRET_KEY`
  (`contatos/limites.py`). Não acrescente coluna com IP em claro.
- **`POST /contato` é a única rota sem CSRF, e isso é decisão escrita** — ver
  `docs/adr/0001-contato-sem-csrf-com-lista-de-origens.md` e o cabeçalho de
  `contatos/origens.py`. Quem protege é a lista de origens, o limite por origem
  de rede, o campo-armadilha e o corpo pequeno. Não estenda `@csrf_exempt` a
  mais nenhuma view.
- **Lista de origens vazia recusa tudo** fora do modo de depuração. Fechado por
  padrão: esquecer de configurar vira 403 visível, não endpoint aberto.
- **Com `USE_HTTPS=True` a aplicação recusa subir** sem `CSRF_TRUSTED_ORIGINS`,
  `CONTATO_CANAL_TITULAR` e `CONTATO_ORIGENS_PERMITIDAS`
  (`contatos/checks.py`). O gatilho é `USE_HTTPS` e não `DEBUG`, porque
  `DEBUG=False` também vale no build e na suíte.
- **CSP estrita, sem exceção**: `default-src 'self'`, vinda de
  `sharedauth.security.montar_csp()`. Nada de `<style>`/`<script>` embutido nem
  atributo `style=` nos templates. Estilo pontual vira classe em
  `static/css/portal.css`. A CI não pega isso; o navegador sim.
- **`django.contrib.admin` não entra.** Ele registra o modelo de usuário
  automaticamente e abre um segundo login, fora do `/login` que o nginx central
  limita. Contas se criam por `manage.py createsuperuser`.
- **`/health` responde com e sem barra**, com o corpo
  `{"servico": "mp-portal", "status": ...}`. O `deploy.sh` e o vigia dependem
  desse formato; não mude sem mudar os dois.
- **A suíte toca o banco.** Foi o achado L01 do levantamento. Teste novo que
  verifique persistência, restrição ou migração usa `pytest.mark.django_db` —
  não `inspect.getsource`, não leitura de arquivo.
- **LF, sem BOM**, em todo arquivo. `.gitattributes` força; um `\r` dentro da
  imagem Linux quebra em silêncio.
- **Acento em texto de interface, nunca em identificador.** Rótulo exibido,
  mensagem de erro e documento levam acento; nome de campo, código de
  `TextChoices`, chave de dicionário, nome de teste e token de log são ASCII.

## Portas

`5601` (aplicação) e `5602` (PostgreSQL), publicadas só em `127.0.0.1`.
Numeração da frota: megasena 51xx, bancário 52xx, renda e conforto 50xx, site
55xx, portal 56xx.

## Suíte

```bash
docker compose --profile quality run --build --rm quality
```

O `--build` **não é opcional**: o serviço `quality` não monta o código do host,
e `docker compose run` sem ele reaproveita a imagem anterior — a suíte passaria
em verde sobre o código de antes.

Diante de vermelho, decida de quem é o defeito antes de mexer: teste que mede
texto literal reprova mudança legítima, e nesse caso quem se corrige é a
asserção. Nunca escreva código para o teste passar.

## Dependências

Faixa no `pyproject.toml` (contrato de compatibilidade, lido pelo Dependabot) e
versão exata no `uv.lock` (o que é testado e servido). As duas camadas têm
papéis diferentes; não troque faixa por `==`. A política da casa é alargar o
teto e preservar o piso.

`sharedauth` vem por referência Git, fixada em tag, **sem o extra `[flask]`** —
o núcleo é Python puro, e pedir o extra traria Flask para dentro de uma imagem
Django.

O lock se regenera em contêiner (não há `uv` no host):

```bash
docker run --rm -v "${PWD}:/w" -w /w python:3.14-slim \
  sh -c "apt-get update -qq && apt-get install -y -qq git && pip install -q uv==0.12.10 && uv lock"
```

## Ligação com o site

O formulário de `/contato` do site ainda **não** aponta para cá. O que precisa
mudar lá, quando o portal for publicado, está em `docs/operacao.md` — são três
ajustes pequenos no `MpSolucoes`, e um deles é renomear o `name` das caixas de
solução.
