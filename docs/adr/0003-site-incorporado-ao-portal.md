# ADR 0003 — O site institucional foi incorporado ao portal

> **REVERTIDA EM 11/10/2026 (ADR 0006).** O site voltou a ser estático, gerado
> por este repositório e servido pela hospedagem compartilhada. O texto abaixo
> é o registro do que foi decidido e por quê.


## Decisão

As sete páginas institucionais da MP Soluções Corporativas deixaram de ser um
site estático servido por nginx no repositório `MpSolucoes` e passaram a ser
servidas por esta aplicação Django. Um repositório, uma imagem, um domínio.

O conteúdo migrou byte a byte; o que mudou foi o envelope:

| Antes | Agora |
|---|---|
| Casca montada por `ssi on` do nginx | `{% include %}` do Django |
| Item ativo do menu por variável SSI | `pagina_ativa`, informado pela view |
| Metadados repetidos no `<head>`, no `map` do nginx e no sitemap | Tabela única em `institucional/paginas.py` |
| `canonical`/`og:url` substituídos pelo nginx | Derivados do request |
| Formulário sem destino | `POST /contato` na mesma rota da página |

## Motivo

**Esta decisão reverte a §L21 do `LEVANTAMENTO_2026-09.md`**, que dizia, com
todas as letras: *"não transforme o site em portal — site institucional
estático e portal autenticado são coisas diferentes, com cadência, risco e
público diferentes. Dois repositórios, dois vhosts."*

O que mudou desde aquela recomendação foi o destino declarado pelo mantenedor
em 08/09/2026: um portal que as pessoas visitam, navegam por várias páginas e
**preenchem formulários** sem autenticar, mais uma área com login que terá
vários serviços, para clientes e para a equipe. Diante disso, os três
argumentos da recomendação original perdem força na ordem inversa da que
tinham:

- **Formulário, no plural.** Num site estático, cada formulário novo repete a
  engenharia de origem, CORS e endpoint separado. Numa aplicação, é uma view.
- **Páginas que vão crescer.** O próprio levantamento anotava que a casca
  compartilhada "é barata hoje, com sete páginas, e cara com trinta".
- **O argumento decisivo é o menu.** Com "Atendimento" no menu do site, o
  cabeçalho, o rodapé e a navegação passariam a existir **duas vezes**, em duas
  linguagens de template, obrigadas a permanecer idênticas para sempre. Essa
  duplicação não dá sintoma no primeiro mês e nunca mais desaparece.

## O que se perde, e é aceito de olhos abertos

**O institucional deixa de ser imune a defeito da aplicação.** Enquanto eram
dois contêineres, um erro no Django não tirava o site do ar. Agora tira.

Três coisas reduzem esse custo, e nenhuma o elimina:

1. **Nenhuma página institucional consulta o banco** — há teste que reprova
   consulta nessas rotas. O conteúdo público continua sendo servido enquanto o
   PostgreSQL não responde;
2. a autocura e o sentinela do VPS já cobrem contêiner `unhealthy` e resposta
   5xx sem mudança nenhuma;
3. **o L06 (medir o RTO) deixa de ser opcional** — ele já estava escrito como
   gatilho para "antes de o portal entrar no ar", e agora o site institucional
   compartilha esse destino.

## O que se ganha além do menu

- **O gatilho do ADR 0001 disparou.** Formulário e destino na mesma origem
  devolvem a proteção CSRF do Django e permitem apagar a lista de origens, o
  CORS e o pré-voo. Menos código, e a defesa padrão do framework no lugar de
  uma feita à mão.
- **Uma fonte para os metadados.** Título, descrição, imagem, item de menu e
  linha do sitemap saem da mesma tabela. Página nova aparece nos três lugares
  sozinha, e há teste comparando.
- **O aviso de privacidade virou link de verdade** no rodapé, onde havia
  `href="#"`. A LGPD exige que ele seja acessível; link morto não é.

## O que foi preservado da fase F5, e não é negociável

- as sete URLs limpas, idênticas, e os `.html` respondendo 301;
- **o domínio não escrito em arquivo nenhum**: `canonical`, `og:url`, `robots`
  e `sitemap` saem do request. Trocar de domínio continua sendo zero edição no
  repositório — o que importa agora que o domínio próprio (L19) está a caminho;
- autossuficiência: nenhuma fonte, imagem ou script vem de host externo;
- CSP fechada — com **uma** folga a mais, `img-src data:`, pelo SVG de ruído do
  `site.css`, e há teste que reprova o aparecimento de uma segunda.

## Gatilho de revisão

**A indisponibilidade do site institucional passar a ter custo maior que o
ganho de manter uma casca só.** Na prática: se a aplicação começar a cair com
frequência que atrapalhe a captação, o caminho de volta não é desincorporar o
site — é servir as páginas públicas por um cache no nginx central, que mantém o
institucional no ar enquanto a aplicação se recupera, sem duplicar a casca.

## Destino do repositório `MpSolucoes`

Arquivado — não apagado — depois que a virada estiver verificada em produção. O
histórico da F5 continua legível, e o `deploy.sh`, o vigia e o monitor externo
perdem a entrada `mp`. Enquanto a virada não acontece, ele continua no ar e
intocado.
