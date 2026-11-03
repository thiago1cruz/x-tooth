import 'dart:convert';
import 'dart:typed_data';

import '../../domain/entities/prediction.dart';

/// Mapeia o JSON da API (`POST /predict`) para a entidade [Prediction].
class PredictionModel extends Prediction {
  const PredictionModel({
    required super.predictedClass,
    required super.confidence,
    required super.probabilities,
    required super.disclaimer,
    super.gradcam,
  });

  factory PredictionModel.fromJson(Map<String, dynamic> json) {
    Uint8List? gradcam;
    final b64 = json['gradcam_png_base64'] as String?;
    if (b64 != null && b64.isNotEmpty) {
      gradcam = base64Decode(b64);
    }
    return PredictionModel(
      predictedClass: json['predicted_class'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      probabilities: (json['probabilities'] as Map<String, dynamic>)
          .map((k, v) => MapEntry(k, (v as num).toDouble())),
      disclaimer: json['disclaimer'] as String? ?? '',
      gradcam: gradcam,
    );
  }
}
