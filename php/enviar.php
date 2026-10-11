<?php
declare(strict_types=1);

/*
 * Recebe o formulario de contato e o encaminha por e-mail. Unico PHP do site.
 *
 * Sem banco, sem sessao e sem gravar a solicitacao: a mensagem segue para a
 * caixa da empresa e e la que ela fica (ver o aviso de privacidade). O que este
 * script grava em disco e so o resumo do endereco de rede, para o limite de
 * envios, e ele e apagado em ate uma hora.
 *
 * A configuracao fica FORA do public_html, em `../contato-config.php` (modelo em
 * `php/contato-config.exemplo.php`). Sem ela o script recusa o envio: o site
 * nunca publica um formulario que nao tem para onde mandar.
 */

const VERSAO_DO_AVISO = '2.0';
const MAX_POR_HORA_POR_ENDERECO = 10;
const MAX_POR_HORA_NO_TOTAL = 60;
const JANELA_EM_SEGUNDOS = 3600;

// Substituidos pelo gerador com as listas de `institucional/paginas.py`.
$SEGMENTOS = /*@@SEGMENTOS@@*/ [];
$SOLUCOES = /*@@SOLUCOES@@*/ [];

date_default_timezone_set('America/Sao_Paulo');

function encerrar_com_erro(int $status, string $mensagem): never
{
    http_response_code($status);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    $molde = @file_get_contents(__DIR__ . '/contato-erro.html');
    $texto = htmlspecialchars($mensagem, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    if ($molde === false) {
        echo '<!DOCTYPE html><meta charset="utf-8"><title>Contato</title><p>' . $texto . '</p>';
    } else {
        echo str_replace('<!--MENSAGEM-->', $texto, $molde);
    }
    exit;
}

function ir_para(string $caminho): never
{
    http_response_code(303);
    header('Location: ' . $caminho);
    exit;
}

function campo(string $nome, int $maximo): string
{
    $valor = $_POST[$nome] ?? '';
    if (!is_string($valor)) {
        return '';
    }
    $valor = trim($valor);
    return mb_substr($valor, 0, $maximo, 'UTF-8');
}

function linha_unica(string $valor): bool
{
    return preg_match('/[\r\n\0]/', $valor) !== 1;
}

/**
 * Conta uma tentativa no arquivo e diz se ainda cabe na janela. O arquivo guarda
 * so os instantes das tentativas recentes.
 */
function cabe_na_janela(string $arquivo, int $maximo): bool
{
    $agora = time();
    $ponteiro = fopen($arquivo, 'c+');
    if ($ponteiro === false) {
        return true; // sem disco para o limite, o honeypot e a validacao seguram
    }
    flock($ponteiro, LOCK_EX);
    $conteudo = stream_get_contents($ponteiro);
    $instantes = array_filter(
        array_map('intval', $conteudo === false || $conteudo === '' ? [] : explode(',', $conteudo)),
        static fn (int $instante): bool => $agora - $instante < JANELA_EM_SEGUNDOS
    );
    $cabe = count($instantes) < $maximo;
    if ($cabe) {
        $instantes[] = $agora;
    }
    ftruncate($ponteiro, 0);
    rewind($ponteiro);
    fwrite($ponteiro, implode(',', $instantes));
    flock($ponteiro, LOCK_UN);
    fclose($ponteiro);
    return $cabe;
}

function limpar_limites(string $pasta): void
{
    foreach (glob($pasta . '/*.txt') ?: [] as $arquivo) {
        if (time() - (int) filemtime($arquivo) > JANELA_EM_SEGUNDOS) {
            @unlink($arquivo);
        }
    }
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    ir_para('/contato');
}

$configuracao = @include dirname(__DIR__) . '/contato-config.php';
if (!is_array($configuracao)
    || !filter_var($configuracao['destino'] ?? '', FILTER_VALIDATE_EMAIL)
    || !filter_var($configuracao['remetente'] ?? '', FILTER_VALIDATE_EMAIL)
    || !is_string($configuracao['segredo'] ?? null)
    || strlen($configuracao['segredo']) < 32
) {
    encerrar_com_erro(503, 'O envio pelo formulário está indisponível no momento.');
}

// Campo-armadilha: resposta identica a de sucesso, sem enviar nada.
if (campo('sobrenome', 200) !== '') {
    ir_para('/contato-enviado');
}

$pasta_limites = dirname(__DIR__) . '/contato-limites';
if (!is_dir($pasta_limites)) {
    @mkdir($pasta_limites, 0700, true);
}
limpar_limites($pasta_limites);
$resumo = hash_hmac('sha256', (string) ($_SERVER['REMOTE_ADDR'] ?? ''), $configuracao['segredo']);
if (!cabe_na_janela($pasta_limites . '/' . $resumo . '.txt', MAX_POR_HORA_POR_ENDERECO)
    || !cabe_na_janela($pasta_limites . '/total.txt', MAX_POR_HORA_NO_TOTAL)
) {
    encerrar_com_erro(429, 'Muitas solicitações em pouco tempo. Tente novamente mais tarde.');
}

$nome = campo('nome', 150);
$empresa = campo('empresa', 150);
$email = campo('email', 254);
$telefone = campo('telefone', 40);
$segmento = campo('segmento', 40);
$mensagem = campo('mensagem', 2000);
$solucoes = [];
foreach ((array) ($_POST['solucoes'] ?? []) as $item) {
    if (is_string($item) && isset($SOLUCOES[$item])) {
        $solucoes[$item] = $SOLUCOES[$item];
    }
}

$erro = null;
if (mb_strlen($nome, 'UTF-8') < 2 || !linha_unica($nome)) {
    $erro = 'Informe o nome de quem está pedindo contato.';
} elseif (!linha_unica($empresa)) {
    $erro = 'Confira o nome da empresa.';
} elseif (!linha_unica($email) || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
    $erro = 'Informe um e-mail válido para podermos responder.';
} elseif (!linha_unica($telefone) || preg_match_all('/\d/', $telefone) < 8) {
    $erro = 'Informe um telefone ou WhatsApp com DDD.';
} elseif ($segmento !== '' && !isset($SEGMENTOS[$segmento])) {
    $erro = 'Escolha um segmento da lista.';
} elseif (campo('consentimento', 10) !== 'on') {
    $erro = 'É preciso concordar com o aviso de privacidade para enviar.';
}
if ($erro !== null) {
    encerrar_com_erro(400, $erro);
}

$agora = date('d/m/Y H:i');
$corpo = "Nova solicitação de contato pelo site.\n\n"
    . "Nome: $nome\n"
    . 'Empresa: ' . ($empresa !== '' ? $empresa : '—') . "\n"
    . "E-mail: $email\n"
    . "Telefone: $telefone\n"
    . 'Segmento: ' . ($SEGMENTOS[$segmento] ?? '—') . "\n"
    . 'Soluções de interesse: ' . ($solucoes !== [] ? implode(', ', $solucoes) : '—') . "\n\n"
    . "Mensagem:\n" . ($mensagem !== '' ? $mensagem : '—') . "\n\n"
    . "--\n"
    . "Consentimento: sim, em $agora (aviso de privacidade v" . VERSAO_DO_AVISO . ").\n"
    . "Responda a este e-mail para falar com quem enviou.\n";

$assunto = '=?UTF-8?B?' . base64_encode('Contato pelo site — ' . $nome) . '?=';
$cabecalhos = [
    'From: =?UTF-8?B?' . base64_encode('Site MP Soluções Corporativas') . '?= <' . $configuracao['remetente'] . '>',
    'Reply-To: ' . $email,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'X-Mailer: enviar.php',
];

$enviado = mail($configuracao['destino'], $assunto, $corpo, implode("\r\n", $cabecalhos), '-f' . $configuracao['remetente']);
if (!$enviado) {
    encerrar_com_erro(502, 'Não foi possível enviar agora. Tente novamente em instantes ou fale conosco por telefone.');
}

ir_para('/contato-enviado');
