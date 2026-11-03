import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../constants/env.dart';
import '../errors/failures.dart';
import 'i_client_http.dart';

class RestClientDioImpl implements IClientHttp {
  final Dio _dio;

  RestClientDioImpl()
      : _dio = Dio(BaseOptions(
          baseUrl: Env.apiBaseUrl,
          connectTimeout: Env.requestTimeout,
          receiveTimeout: Env.requestTimeout,
        ));

  @override
  Future<ClientResponse> get(String path) async {
    try {
      final res = await _dio.get(path);
      return ClientResponse(statusCode: res.statusCode ?? 0, data: res.data);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  @override
  Future<ClientResponse> postFile(
    String path, {
    required Uint8List bytes,
    required String filename,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final form = FormData.fromMap({
        'file': MultipartFile.fromBytes(bytes, filename: filename),
      });
      final res = await _dio.post(
        path,
        data: form,
        queryParameters: queryParameters,
      );
      return ClientResponse(statusCode: res.statusCode ?? 0, data: res.data);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Failure _mapError(DioException e) {
    if (e.response?.statusCode == 400) return const InvalidImageFailure();
    switch (e.type) {
      case DioExceptionType.connectionError:
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return const NetworkFailure();
      default:
        return const UnexpectedFailure();
    }
  }
}
