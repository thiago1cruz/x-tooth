import 'dart:typed_data';

import '../../../../core/client/i_client_http.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/prediction.dart';
import '../../domain/repositories/i_diagnosis_repository.dart';
import '../models/prediction_model.dart';

class DiagnosisRepositoryImpl implements IDiagnosisRepository {
  final IClientHttp _client;

  DiagnosisRepositoryImpl(this._client);

  @override
  Future<Prediction> classify({
    required Uint8List imageBytes,
    required String filename,
    bool withGradcam = true,
  }) async {
    final res = await _client.postFile(
      '/predict',
      bytes: imageBytes,
      filename: filename,
      queryParameters: {'gradcam': withGradcam ? 1 : 0},
    );

    if (res.statusCode != 200 || res.data is! Map<String, dynamic>) {
      throw const UnexpectedFailure();
    }
    return PredictionModel.fromJson(res.data as Map<String, dynamic>);
  }
}
