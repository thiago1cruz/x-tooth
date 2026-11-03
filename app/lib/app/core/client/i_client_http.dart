import 'dart:typed_data';

/// Resposta padronizada do client HTTP.
class ClientResponse {
  final int statusCode;
  final dynamic data;
  const ClientResponse({required this.statusCode, required this.data});
}

/// Abstração do client HTTP do app (implementação atual: Dio).
abstract interface class IClientHttp {
  Future<ClientResponse> get(String path);

  /// Envia um arquivo (multipart, campo `file`).
  Future<ClientResponse> postFile(
    String path, {
    required Uint8List bytes,
    required String filename,
    Map<String, dynamic>? queryParameters,
  });
}
