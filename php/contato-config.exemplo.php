<?php
declare(strict_types=1);

/*
 * Modelo da configuracao do formulario. Copie para `contato-config.php` na pasta
 * ACIMA do public_html (ex.: .../domains/<dominio>/contato-config.php) e
 * preencha. Nunca coloque este arquivo dentro do public_html nem no Git.
 */
return [
    // Caixa que recebe as solicitacoes.
    'destino' => 'comercial@exemplo.com.br',
    // Endereco do proprio dominio, usado como remetente. Precisa existir na
    // hospedagem, ou o provedor descarta a mensagem.
    'remetente' => 'contato@exemplo.com.br',
    // Chave do resumo do endereco de rede (limite de envios). 32 caracteres ou
    // mais, aleatorios. Gere com: php -r "echo bin2hex(random_bytes(24));"
    'segredo' => 'troque-por-um-valor-aleatorio-de-48-caracteres-no-minimo',
];
