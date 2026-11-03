/// Falhas de domínio do X-Tooth.
sealed class Failure implements Exception {
  final String message;
  const Failure(this.message);
}

/// API inacessível (offline, IP errado, servidor parado).
class NetworkFailure extends Failure {
  const NetworkFailure([
    super.message =
        'Não foi possível conectar ao servidor. Verifique se a API está em execução e o endereço configurado.',
  ]);
}

/// Arquivo enviado não é uma imagem válida (HTTP 400 da API).
class InvalidImageFailure extends Failure {
  const InvalidImageFailure([
    super.message = 'O arquivo selecionado não é uma imagem válida.',
  ]);
}

/// Erro inesperado da API ou do app.
class UnexpectedFailure extends Failure {
  const UnexpectedFailure([
    super.message = 'Ocorreu um erro inesperado. Tente novamente.',
  ]);
}
