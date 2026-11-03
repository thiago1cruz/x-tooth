import 'package:flutter/material.dart';
import 'package:flutter_modular/flutter_modular.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/ui/components/disclaimer_banner.dart';
import '../../domain/states/diagnosis_state.dart';
import '../../viewmodel/diagnosis_viewmodel.dart';
import '../components/result_card.dart';

class DiagnosisPage extends StatefulWidget {
  const DiagnosisPage({super.key});

  @override
  State<DiagnosisPage> createState() => _DiagnosisPageState();
}

class _DiagnosisPageState extends State<DiagnosisPage> {
  final viewmodel = Modular.get<DiagnosisViewmodel>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('X-Tooth')),
      body: SafeArea(
        child: AnimatedBuilder(
          animation: viewmodel,
          builder: (context, _) {
            final state = viewmodel.state;
            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const DisclaimerBanner(),
                  const SizedBox(height: 20),
                  _buildImageArea(state),
                  const SizedBox(height: 20),
                  _buildActions(state),
                  if (state is DiagnosisError) ...[
                    const SizedBox(height: 16),
                    _ErrorBox(message: state.message),
                  ],
                  if (state is DiagnosisSuccess) ...[
                    const SizedBox(height: 20),
                    ResultCard(prediction: state.prediction),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildImageArea(DiagnosisState state) {
    final bytes = switch (state) {
      DiagnosisImageSelected(:final imageBytes) => imageBytes,
      DiagnosisLoading(:final imageBytes) => imageBytes,
      DiagnosisSuccess(:final imageBytes) => imageBytes,
      DiagnosisError(:final imageBytes) => imageBytes,
      _ => null,
    };

    return GestureDetector(
      onTap: state is DiagnosisLoading ? null : viewmodel.pickImage,
      child: Container(
        height: 280,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFCBD5E1)),
        ),
        clipBehavior: Clip.antiAlias,
        child: bytes == null
            ? const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.file_upload_outlined,
                      size: 56, color: AppTheme.primary),
                  SizedBox(height: 12),
                  Text(
                    'Toque para selecionar a radiografia\n(arquivo digital periapical)',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black54),
                  ),
                ],
              )
            : Stack(
                fit: StackFit.expand,
                children: [
                  Image.memory(bytes, fit: BoxFit.contain),
                  if (state is DiagnosisLoading)
                    Container(
                      color: Colors.black45,
                      child: const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircularProgressIndicator(color: Colors.white),
                            SizedBox(height: 12),
                            Text('Analisando...',
                                style: TextStyle(color: Colors.white)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }

  Widget _buildActions(DiagnosisState state) {
    return switch (state) {
      DiagnosisImageSelected() => FilledButton.icon(
          onPressed: viewmodel.classify,
          icon: const Icon(Icons.biotech_outlined),
          label: const Text('Analisar radiografia'),
        ),
      DiagnosisSuccess() || DiagnosisError() => OutlinedButton.icon(
          onPressed: viewmodel.reset,
          icon: const Icon(Icons.refresh),
          label: const Text('Nova análise'),
        ),
      _ => const SizedBox.shrink(),
    };
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  const _ErrorBox({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.danger.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.danger.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.danger),
          const SizedBox(width: 10),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}
