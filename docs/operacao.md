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

O DNS fica no registro.br (servidores `a.auto.dns.br` e `b.auto.dns.br`, DNSSEC
ligado). Na zona:

- `A` de `@` e de `www` apontando para o IP do servidor da hospedagem (hPanel →
  Site → dados do servidor).
- Registros de e-mail (`MX`, SPF, DKIM, DMARC): **ainda não**, ver abaixo.

Trocar o IP da hospedagem exige trocar os dois registros `A`.

## O que ficou aberto

- **E-mail do domínio.** Não contratado. Endereços desejados: `luiz`, `marcelo`,
  `felipe`, `financeiro`, `contato`, `comercial`, `operacional`, `rh`,
  `licitacoes`. O site já publica `contato@mp-solucoes.seg.br`, que **ainda não
  existe**: quem escrever recebe devolução. Falta decidir com a Hostinger o
  plano e a quantidade de caixas; depois: criar as caixas e apelidos, publicar
  `MX`/SPF/DKIM/DMARC no registro.br, preencher o `contato-config.php`, gerar com
  `COM_FORMULARIO=1` e testar envio e recebimento. O aviso de privacidade usa
  `contato@` como canal do titular.
- **Entregabilidade do formulário.** O `enviar.php` usa `mail()`. Sem SPF/DKIM do
  domínio, as mensagens podem cair em spam; reavaliar (SMTP autenticado) depois
  que o e-mail existir.
- **Endereço de rede no limite de envios.** O script usa `REMOTE_ADDR`. Se a
  hospedagem estiver atrás de proxy, todos os visitantes parecem o mesmo
  endereço e o teto de 10 envios por hora passa a valer para o site inteiro;
  conferir quando o formulário entrar no ar.
- **VPS antigo** (`mp-solucoes.duckdns.org`): a desativação é do mantenedor.
  Depois dela, remover o portal do repositório `manutencao` (`deploy.sh`, vigia,
  timers `expurgo-contatos` e `aviso-contatos`) e o projeto `mp_portal_vps` do
  BackupRestore. Nada disso foi tocado.
- **`main` sem proteção de branch (L11).** O fluxo é por pull request com squash
  mesmo assim.
