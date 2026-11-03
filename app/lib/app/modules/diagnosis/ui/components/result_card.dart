import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/entities/prediction.dart';

/// Exibe o resultado: classe predita, confiança, probabilidades e Grad-CAM.
class ResultCard extends StatelessWidget {
  final Prediction prediction;
  const ResultCard({super.key, required this.prediction});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Resultado da análise',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _MainPrediction(prediction: prediction),
            const SizedBox(height: 16),
            const Text('Probabilidades por classe',
                style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            ...prediction.rankedProbabilities.map(
              (e) => _ProbabilityBar(
                label: e.key,
                value: e.value,
                highlight: e.key == prediction.predictedClass,
              ),
            ),
            if (prediction.gradcam != null) ...[
              const SizedBox(height: 16),
              const Text('Mapa de atenção (Grad-CAM)',
                  style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              const Text(
                'Regiões que mais influenciaram a classificação.',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(prediction.gradcam!, fit: BoxFit.contain),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MainPrediction extends StatelessWidget {
  final Prediction prediction;
  const _MainPrediction({required this.prediction});

  @override
  Widget build(BuildContext context) {
    final pct = (prediction.confidence * 100).toStringAsFixed(1);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.medical_services_outlined,
              color: AppTheme.primary, size: 32),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  prediction.predictedClass,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.bold),
                ),
                Text('Confiança: $pct%',
                    style: const TextStyle(color: Colors.black54)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProbabilityBar extends StatelessWidget {
  final String label;
  final double value;
  final bool highlight;
  const _ProbabilityBar({
    required this.label,
    required this.value,
    required this.highlight,
  });

  @override
  Widget build(BuildContext context) {
    final pct = (value * 100).toStringAsFixed(1);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight:
                        highlight ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
              ),
              Text('$pct%', style: const TextStyle(fontSize: 12.5)),
            ],
          ),
          const SizedBox(height: 3),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: value,
              minHeight: 6,
              backgroundColor: const Color(0xFFE2E8F0),
              color: highlight ? AppTheme.primary : const Color(0xFF94A3B8),
            ),
          ),
        ],
      ),
    );
  }
}
