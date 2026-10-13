# Operação

O site é estático e roda na **hospedagem compartilhada da Hostinger** (plano
Unlimited Web Hosting, pedido 1010158973), no domínio `mp-solucoes.seg.br`,
registrado no registro.br. Não há servidor para manter: o que está no ar é a
pasta `dist/site`, gerada por este repositório.

Decisão e motivo: `docs/adr/0006-site-estatico-na-hospedagem-compartilhada.md`.

## Como publicar

1. Gerar o site (o domínio é parâmetro):

   ```bash
   DOMINIO=mp-solucoes.seg.br docker compose run --build --rm gerar
   ```

   Com `COM_FORMULARIO=1` a página de contato traz o formulário e a saída
   inclui o `enviar.php`. Só use quando a configuração do formulário existir no
   servidor (abaixo).

2. Compactar `dist/site` e enviar o conteúdo para `public_html` (a raiz do
   site, `/home/<usuario>/domains/mp-solucoes.seg.br/public_html`): pelo
   Gerenciador de Arquivos do hPanel ou pela API da Hostinger (upload do `.zip`
   e implantação de arquivo estático). A implantação **substitui o conteúdo do
   `public_html`**: o que mora lá fora do que o gerador produz é apagado. Por
   isso a configuração do formulário fica um nível acima.

3. Conferir no navegador: as sete páginas, `/privacidade`, o redirecionamento
   `http` → `https`, `/solucoes.html` → `/solucoes` (301) e a página 404.

## Formulário de contato

O `enviar.php` lê `../contato-config.php`, ou seja, **um nível acima do
`public_html`** (modelo em `php/contato-config.exemplo.php`):

- `destino`: a caixa que recebe as solicitações;
- `remetente`: endereço do próprio domínio (precisa existir na hospedagem);
- `segredo`: 32+ caracteres aleatórios (`php -r "echo bin2hex(random_bytes(24));"`).

Sem esse arquivo o script responde 503 e o site não perde nada: só não deve ser
publicado com `COM_FORMULARIO=1`. Ele cria `../contato-limites/` sozinho (resumos
de endereço de rede, apagados em até uma hora).

**Retenção.** O aviso de privacidade promete apagar as solicitações em até 24
meses se não virarem contrato. Como não há banco, isso é feito **à mão, na caixa
de e-mail que recebe** — vale um lembrete recorrente.

## DNS (registro.br)

O site está no ar em `https://mp-solucoes.seg.br` desde 11/10/2026. O DNS fica no
registro.br (servidores `a.auto.dns.br` e `b.auto.dns.br`, DNSSEC ligado), e a
zona editada em **Modo avançado** (o painel só volta ao modo básico depois de 2
horas da troca) tem:

| Tipo | Nome | Valor |
|---|---|---|
| A | `mp-solucoes.seg.br` | `185.239.210.159` (IP do servidor na Hostinger) |
| CNAME | `www.mp-solucoes.seg.br` | `mp-solucoes.seg.br` |

O certificado HTTPS é emitido pela Hostinger. Trocar o IP da hospedagem exige
trocar o registro `A`. Os registros de e-mail estão na seção seguinte.

## E-mail do domínio

Plano Starter Business Email (gratuito por 12 meses), contratado no hPanel. São
nove caixas, todas separadas, sem apelidos: `luiz`, `marcelo`, `felipe`,
`financeiro`, `contato`, `comercial`, `operacional`, `rh` e `licitacoes`,
todas `@mp-solucoes.seg.br`. As senhas são definidas no hPanel por quem as usa.

Registros adicionais da zona no registro.br:

| Tipo | Nome | Valor |
|---|---|---|
| TXT | `@` | verificação de domínio da Hostinger |
| MX | `@` | `5 mx1.hostinger.com` e `10 mx2.hostinger.com` |
| TXT | `@` | `v=spf1 include:_spf.mail.hostinger.com ~all` |
| TXT | `_dmarc` | `v=DMARC1; p=none` |
| CNAME | `hostingermail-a/b/c._domainkey` | `hostingermail-a/b/c.dkim.mail.hostinger.com` |

O formulário está ligado desde 11/10/2026: o site é gerado com
`COM_FORMULARIO=1`, e o `../contato-config.php` aponta `destino` e `remetente`
para `contato@`. Testado de ponta a ponta (chegada na caixa, Reply-To para o
e-mail informado no formulário, resposta recebida). O arquivo foi enviado pela
API de upload da Hostinger para a pasta acima do `public_html`; o deploy do
`site.zip` só substitui o `public_html`, então ele sobrevive às publicações.

## O que ficou aberto

- **Renovação do e-mail.** O e-mail do domínio roda no período gratuito de 12
  meses do plano Starter Business Email (até 12/10/2027). Desligar a renovação
  automática em hPanel > Cobrança, ou decidir o plano pago antes do vencimento.
- **Retenção e DMARC.** A retenção de 24 meses é manual (ver acima) e o DMARC
  está em `p=none`; endurecer depois de observar os relatórios.
- **Endereço de rede no limite de envios.** O script usa `REMOTE_ADDR`. Se a
  hospedagem estiver atrás de proxy, todos os visitantes parecem o mesmo
  endereço e o teto de 10 envios por hora passa a valer para o site inteiro;
  ainda não conferido (o teste de 11/10 usou um endereço só).
- **VPS antigo** (`mp-solucoes.duckdns.org`): a desativação é do mantenedor.
  Depois dela, remover o portal do repositório `manutencao` (`deploy.sh`, vigia,
  timers `expurgo-contatos` e `aviso-contatos`) e o projeto `mp_portal_vps` do
  BackupRestore. Nada disso foi tocado.
- **`main` sem proteção de branch (L11).** O fluxo é por pull request com squash
  mesmo assim.
