import 'dart:typed_data';

import '../entities/prediction.dart';

abstract interface class IDiagnosisRepository {
  /// Envia a radiografia (bytes do arquivo) e retorna a predição.
  ///
  /// [withGradcam]: quando true, a API devolve também o mapa Grad-CAM.
  Future<Prediction> classify({
    required Uint8List imageBytes,
    required String filename,
    bool withGradcam = true,
  });
}
