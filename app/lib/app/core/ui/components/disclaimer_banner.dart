import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

/// Aviso ético exibido em todas as telas de resultado:
/// a ferramenta auxilia, não substitui o profissional.
class DisclaimerBanner extends StatelessWidget {
  final String text;
  const DisclaimerBanner({
    super.key,
    this.text =
        'Ferramenta de auxílio ao diagnóstico. O resultado não substitui a '
        'avaliação de um profissional de odontologia.',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppTheme.warning, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 12.5, color: Colors.black87),
            ),
          ),
        ],
      ),
    );
  }
}
