# MP Portal — guia de trabalho

## Escopo e fontes de verdade

Gerador do site estático da MP Soluções Corporativas. O único artefato
publicável é `dist/site`; a hospedagem não executa a aplicação. Leia
`README.md`, `docs/operacao.md`, `docs/TESTES.md` e os ADRs antes de mudar
geração, formulário ou publicação. Use os comandos Docker documentados; não
instale ferramentas no host.

## Limites que não podem mudar por acidente

- Metadados, menu e sitemap têm uma fonte: `institucional/paginas.py`.
- O domínio é parâmetro de geração (`DOMINIO`), nunca valor fixado no fonte.
- Formulário só entra com `COM_FORMULARIO=1`; sua configuração fica fora de
  `public_html` e do Git. Mudança nos dados tratados exige atualizar o aviso de
  privacidade.
- Mantenha CSP restrita, recursos locais por padrão, URLs limpas e arquivos
  estáticos gerados pelo mecanismo `{% static %}`.

## Validação proporcional

| Mudança | Validação mínima antes de concluir |
| --- | --- |
| Documentação ou conteúdo | Gerar o site e revisar páginas, links e metadados afetados. |
| Python, template, CSS ou ativo | `docker compose run --build --rm quality`; abrir a prévia local quando houver efeito visual. |
| PHP, formulário, privacidade ou `.htaccess` | Além da suíte, gerar com `COM_FORMULARIO=1` e executar o teste PHP do README. |
| Compose, Dockerfile ou dependência | `docker compose config --quiet` e a suíte. Regenerar o lock somente no contêiner, conforme README. |
| Publicação | Seguir checklist e rollback em `docs/operacao.md`; conferir site e redirecionamentos após upload. Não publicar nem alterar DNS/e-mail sem autorização explícita. |

Testes verificam comportamento e risco, não texto ou implementação acidental.
Se uma asserção já não representa a regra, corrija-a antes de mudar produção.
