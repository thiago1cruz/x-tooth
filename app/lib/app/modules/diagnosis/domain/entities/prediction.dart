import 'dart:typed_data';

/// Resultado da classificação de uma radiografia periapical.
class Prediction {
  final String predictedClass;
  final double confidence;
  final Map<String, double> probabilities;
  final String disclaimer;

  /// Mapa de calor Grad-CAM (PNG) — onde o modelo concentrou a atenção.
  final Uint8List? gradcam;

  const Prediction({
    required this.predictedClass,
    required this.confidence,
    required this.probabilities,
    required this.disclaimer,
    this.gradcam,
  });

  /// Probabilidades ordenadas da maior para a menor.
  List<MapEntry<String, double>> get rankedProbabilities {
    final list = probabilities.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return list;
  }
}
