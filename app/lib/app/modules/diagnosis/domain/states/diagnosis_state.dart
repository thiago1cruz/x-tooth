import 'dart:typed_data';

import '../entities/prediction.dart';

/// Estados da tela de diagnóstico (MVVM).
sealed class DiagnosisState {
  const DiagnosisState();
}

/// Nenhuma imagem selecionada ainda.
class DiagnosisInitial extends DiagnosisState {
  const DiagnosisInitial();
}

/// Imagem selecionada, aguardando envio.
class DiagnosisImageSelected extends DiagnosisState {
  final Uint8List imageBytes;
  final String filename;
  const DiagnosisImageSelected({
    required this.imageBytes,
    required this.filename,
  });
}

/// Envio/classificação em andamento.
class DiagnosisLoading extends DiagnosisState {
  final Uint8List imageBytes;
  const DiagnosisLoading({required this.imageBytes});
}

/// Classificação concluída.
class DiagnosisSuccess extends DiagnosisState {
  final Uint8List imageBytes;
  final Prediction prediction;
  const DiagnosisSuccess({
    required this.imageBytes,
    required this.prediction,
  });
}

/// Falha (rede, arquivo inválido, erro inesperado).
class DiagnosisError extends DiagnosisState {
  final String message;
  final Uint8List? imageBytes;
  const DiagnosisError({required this.message, this.imageBytes});
}
