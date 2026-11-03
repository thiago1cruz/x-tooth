import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/errors/failures.dart';
import '../domain/repositories/i_diagnosis_repository.dart';
import '../domain/states/diagnosis_state.dart';

/// ViewModel (MVVM) da tela de diagnóstico.
///
/// Entrada da ferramenta: SOMENTE upload de arquivo da radiografia digital
/// (galeria/arquivos). Captura por câmera fica fora do escopo validado.
class DiagnosisViewmodel extends ChangeNotifier {
  final IDiagnosisRepository _repository;
  final ImagePicker _picker = ImagePicker();

  DiagnosisViewmodel(this._repository);

  DiagnosisState _state = const DiagnosisInitial();
  DiagnosisState get state => _state;

  void _emit(DiagnosisState s) {
    _state = s;
    notifyListeners();
  }

  Future<void> pickImage() async {
    final file = await _picker.pickImage(source: ImageSource.gallery);
    if (file == null) return;
    final bytes = await file.readAsBytes();
    _emit(DiagnosisImageSelected(imageBytes: bytes, filename: file.name));
  }

  Future<void> classify() async {
    final current = _state;
    if (current is! DiagnosisImageSelected) return;

    _emit(DiagnosisLoading(imageBytes: current.imageBytes));
    try {
      final prediction = await _repository.classify(
        imageBytes: current.imageBytes,
        filename: current.filename,
      );
      _emit(DiagnosisSuccess(
        imageBytes: current.imageBytes,
        prediction: prediction,
      ));
    } on Failure catch (f) {
      _emit(DiagnosisError(message: f.message, imageBytes: current.imageBytes));
    } catch (_) {
      _emit(DiagnosisError(
        message: const UnexpectedFailure().message,
        imageBytes: current.imageBytes,
      ));
    }
  }

  void reset() => _emit(const DiagnosisInitial());
}
