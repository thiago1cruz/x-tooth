/// Configurações de ambiente do X-Tooth.
///
/// [apiBaseUrl]: endereço da API que serve o modelo.
/// - Simulador iOS: http://localhost:8000
/// - Emulador Android: http://10.0.2.2:8000
/// - Dispositivo físico: http://<IP-do-Mac-na-rede>:8000
abstract class Env {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const Duration requestTimeout = Duration(seconds: 60);
}
