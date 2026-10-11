# ADR 0006 — O site volta a ser estático, na hospedagem compartilhada

**Data:** 11/10/2026

## Contexto

O portal era uma aplicação Django com PostgreSQL, num VPS dedicado, em
`mp-solucoes.duckdns.org` (ADR 0003): site institucional, formulário de contato
gravado em banco, painel com tarefas, atendimento e contas.

Dois fatos mudaram o desenho:

- A empresa contratou o plano **Unlimited Web Hosting** da Hostinger — hospedagem
  compartilhada, que serve arquivos estáticos e PHP/MySQL, e **não** roda
  Django, PostgreSQL nem Docker.
- O mantenedor decidiu que o VPS deixa de existir, que o quadro de tarefas não é
  mais usado e que os contatos gravados eram de teste (o site nunca esteve em
  produção real). O domínio definitivo é `mp-solucoes.seg.br`, registrado no
  registro.br.

## Decisão

O repositório passa a ser o **gerador de um site estático**:

- `institucional/gerador.py` renderiza os templates de `templates/site/` (o
  Django entra só como motor de template, em tempo de build) e monta a pasta
  `dist/site`: páginas em `.html`, `robots.txt`, `sitemap.xml`, `.htaccess`,
  os arquivos de `static/` e, quando ligado, o `enviar.php`.
- **O domínio é parâmetro do gerador** (`--dominio`), e não está escrito em
  arquivo nenhum do repositório: `canonical`, `og:url`, sitemap e os endereços
  de e-mail saem dele.
- **O formulário de contato é um único PHP** (`php/enviar.php`) que valida e
  envia a solicitação por e-mail para uma caixa da empresa. Sem banco, sem
  sessão, sem gravar a solicitação: ela fica na caixa de e-mail. O destino mora
  num arquivo de configuração **fora** do `public_html`. O formulário só é
  publicado com `--com-formulario`, porque depende de uma caixa que receba — sem
  ela, a página de contato mostra telefone, WhatsApp e e-mail.
- **A CSP e os cabecalhos de segurança** continuam vindo de
  `sharedauth.security`, agora gravados no `.htaccess`.
- **O aviso de privacidade foi reescrito** (versão 2.0): não há banco; a
  Hostinger é operadora (hospedagem e e-mail); o endereço de rede só existe como
  resumo criptográfico por até uma hora, para o limite de envios.
- A suíte gera o site de verdade e confere a saída (`tests/test_gerador.py`); o
  `php/testar.sh` exercita o `enviar.php` num contêiner `php:cli`.

Foram removidos: `tarefas`, `contas`, `contatos` (modelo, migrações, painel de
atendimento, expurgo, aviso de chegada), `core`, `portal`, PostgreSQL, Gunicorn,
WhiteNoise, o `compose` de produção e a CI de implantação.

## O que isto reverte

- **ADR 0003** (site incorporado ao portal): revertida — o site voltou a ser
  estático, só que agora gerado a partir do mesmo repositório.
- **ADR 0004** (tarefas) e **ADR 0005** (área logada): sem efeito — o painel
  deixou de existir.
- **ADR 0001** e **ADR 0002**: permanecem como registro histórico.

## Consequências

- **Ganho:** nada para manter no servidor; sem banco, sem atualização de
  sistema, sem backup do portal. O site publicado é um conjunto de arquivos.
- **Perda assumida:** não há mais triagem de atendimento nem histórico de
  solicitações em sistema próprio. A caixa de e-mail é o único registro, e
  **a retenção de 24 meses que o aviso promete passa a ser feita à mão**, na
  caixa.
- **Dependência nova:** o formulário usa `mail()` do PHP da hospedagem. A
  entregabilidade depende de SPF/DKIM do domínio, que só existem depois que o
  e-mail da empresa for contratado e o DNS configurado.
- **Gatilho para reabrir:** se voltar a ser necessário área restrita, banco ou
  triagem de atendimento, não cabe na hospedagem compartilhada — a decisão
  seria um VPS ou um serviço próprio, e este ADR seria revisto.
