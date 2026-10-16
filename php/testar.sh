#!/bin/sh
# Teste de ponta a ponta do `enviar.php`, dentro de um conteiner `php:cli`:
#
#   python -m institucional.gerador --dominio exemplo.com.br --saida dist/site --com-formulario
#   docker run --rm -v "$PWD/php:/php:ro" -v "$PWD/dist/site:/site:ro" php:8.3-cli sh /php/testar.sh
#
# Sobe o servidor embutido sobre a saida do gerador, com uma configuracao de
# teste FORA da raiz publica (como na hospedagem) e um `sendmail` falso que
# guarda a mensagem num arquivo. Sai com codigo diferente de zero no primeiro
# comportamento errado.
set -eu

RAIZ=/tmp/hospedagem
rm -rf "$RAIZ"
mkdir -p "$RAIZ"
cp -r /site "$RAIZ/public_html"
cat > "$RAIZ/contato-config.php" <<'FIM'
<?php
return [
    'destino' => 'comercial@exemplo.com.br',
    'remetente' => 'contato@exemplo.com.br',
    'segredo' => 'segredo-de-teste-com-mais-de-trinta-e-dois-caracteres',
];
FIM
cat > /tmp/sendmail-falso.sh <<'FIM'
#!/bin/sh
cat > /tmp/mensagem.txt
FIM
chmod +x /tmp/sendmail-falso.sh

iniciar_servidor() {
    php -d sendmail_path=/tmp/sendmail-falso.sh -S 127.0.0.1:8099 -t "$RAIZ/public_html" >/tmp/servidor.log 2>&1 &
    SERVIDOR=$!
    sleep 1
}

iniciar_servidor
trap 'kill $SERVIDOR 2>/dev/null || true' EXIT

URL=http://127.0.0.1:8099/enviar.php

# Devolve o codigo HTTP e deixa o corpo em /tmp/corpo.html.
enviar() {
    php -r '
        $contexto = stream_context_create(["http" => [
            "method" => "POST",
            "header" => "Content-Type: application/x-www-form-urlencoded",
            "content" => $argv[2],
            "ignore_errors" => true,
            "follow_location" => 0,
        ]]);
        $corpo = file_get_contents($argv[1], false, $contexto);
        file_put_contents("/tmp/corpo.html", $corpo);
        preg_match("#HTTP/\S+ (\d+)#", $http_response_header[0], $m);
        $local = "";
        foreach ($http_response_header as $linha) {
            if (stripos($linha, "Location:") === 0) { $local = trim(substr($linha, 9)); }
        }
        echo $m[1], " ", $local;
    ' "$URL" "$1"
}

esperar() {
    obtido="$(enviar "$2")"
    if [ "$obtido" != "$1" ]; then
        echo "FALHOU: esperado '$1', obtido '$obtido' para: $2" >&2
        cat /tmp/servidor.log >&2
        exit 1
    fi
    echo "ok: $3"
}

VALIDO='nome=Maria+Souza&empresa=Condominio+Alfa&email=maria%40exemplo.com.br&telefone=%2811%29+98888-7777&segmento=condominios&solucoes%5B%5D=portaria&solucoes%5B%5D=facilities&mensagem=Preciso+de+portaria+remota&consentimento=on'

rm -f /tmp/mensagem.txt
esperar "303 /contato-enviado" "$VALIDO" "envio valido redireciona para a confirmacao"
grep -q '^To: comercial@exemplo.com.br' /tmp/mensagem.txt || { echo "FALHOU: destinatario" >&2; exit 1; }
grep -q '^Reply-To: maria@exemplo.com.br' /tmp/mensagem.txt || { echo "FALHOU: Reply-To" >&2; exit 1; }
grep -q 'Soluções de interesse: Portaria e recepção, Facilities' /tmp/mensagem.txt || { echo "FALHOU: solucoes" >&2; cat /tmp/mensagem.txt >&2; exit 1; }
grep -q 'Consentimento: sim' /tmp/mensagem.txt || { echo "FALHOU: consentimento no corpo" >&2; exit 1; }
echo "ok: mensagem montada com destino, Reply-To, solucoes e consentimento"

rm -f /tmp/mensagem.txt
esperar "303 /contato-enviado" "${VALIDO}&sobrenome=robo" "armadilha responde como sucesso"
test ! -e /tmp/mensagem.txt || { echo "FALHOU: armadilha enviou e-mail" >&2; exit 1; }
echo "ok: armadilha nao envia nada"

esperar "400 " "${VALIDO%%&consentimento=on}" "sem consentimento e recusado"
grep -q 'concordar com o aviso' /tmp/corpo.html || { echo "FALHOU: mensagem de consentimento" >&2; exit 1; }
esperar "400 " 'nome=A&email=maria%40exemplo.com.br&telefone=11988887777&consentimento=on' "nome curto e recusado"
esperar "400 " 'nome=Maria&email=invalido&telefone=11988887777&consentimento=on' "e-mail invalido e recusado"
esperar "400 " 'nome=Maria&email=maria%40exemplo.com.br&telefone=123&consentimento=on' "telefone curto e recusado"
esperar "400 " 'nome=Maria%0D%0ABcc%3A+x%40y.com&email=maria%40exemplo.com.br&telefone=11988887777&consentimento=on' "quebra de linha no nome e recusada"
esperar "400 " 'nome=Maria&email=maria%40exemplo.com.br%0D%0ABcc%3A+x%40y.com&telefone=11988887777&consentimento=on' "injecao de cabecalho no e-mail e recusada"
esperar "400 " 'nome=Maria&email=maria%40exemplo.com.br&telefone=11988887777&segmento=inexistente&consentimento=on' "segmento fora da lista e recusado"

# GET nao envia: volta para o formulario.
obtido="$(php -r '
    $c = stream_context_create(["http" => ["ignore_errors" => true, "follow_location" => 0]]);
    file_get_contents($argv[1], false, $c);
    preg_match("#HTTP/\S+ (\d+)#", $http_response_header[0], $m);
    echo $m[1];
' "$URL")"
[ "$obtido" = "303" ] || { echo "FALHOU: GET devolveu $obtido" >&2; exit 1; }
echo "ok: GET volta para o formulario"

# Limite por endereco (10 por hora): os envios acima ja gastaram 8; os quatro
# seguintes passam de 10 e o ultimo tem de voltar 429. A armadilha sai antes
# do limite e nao conta.
for i in 1 2 3 4; do enviar "$VALIDO" >/dev/null; done
esperar "429 " "$VALIDO" "limite por endereco devolve 429"

# Sem configuracao, o formulario nao envia.
rm "$RAIZ/contato-config.php"
rm -rf "$RAIZ/contato-limites"
# Teste a ausencia de configuracao num worker novo, sem estado de include ou
# cache de caminhos do worker que ja leu o arquivo nos casos anteriores.
kill "$SERVIDOR" 2>/dev/null || true
wait "$SERVIDOR" 2>/dev/null || true
iniciar_servidor
esperar "503 " "$VALIDO" "sem configuracao devolve 503"
echo "TUDO OK"
