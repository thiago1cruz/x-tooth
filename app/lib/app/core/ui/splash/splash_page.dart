import 'package:flutter/material.dart';
import 'package:flutter_modular/flutter_modular.dart';

import '../../client/i_client_http.dart';
import '../../theme/app_theme.dart';

/// Splash com verificação de disponibilidade da API (`GET /health`).
/// Sucesso → entra no app. Falha → estado vazio de serviço indisponível,
/// com opção de tentar novamente.
class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  final _client = Modular.get<IClientHttp>();
  bool _unavailable = false;

  @override
  void initState() {
    super.initState();
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    setState(() => _unavailable = false);
    // Tempo mínimo de exibição da marca + chamada ao /health em paralelo.
    final results = await Future.wait<dynamic>([
      Future.delayed(const Duration(seconds: 2)),
      _client.get('/health').then<Object?>((r) => r).catchError((e) => e),
    ]);

    final health = results[1];
    final ok = health is ClientResponse && health.statusCode == 200;

    if (!mounted) return;
    if (ok) {
      Modular.to.navigate('/diagnosis/');
    } else {
      setState(() => _unavailable = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primary,
      body: Center(
        child: _unavailable ? _buildUnavailable() : _buildBranding(),
      ),
    );
  }

  Widget _buildBranding({bool withLoader = true}) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.12),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.medical_information_outlined,
              size: 64, color: Colors.white),
        ),
        const SizedBox(height: 24),
        const Text(
          'X-Tooth',
          style: TextStyle(
            color: Colors.white,
            fontSize: 36,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 8),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 48),
          child: Text(
            'Auxílio ao diagnóstico de lesões endo-periodontais',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
        ),
        if (withLoader) ...[
          const SizedBox(height: 32),
          const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(
              color: Colors.white70,
              strokeWidth: 2.5,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildUnavailable() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.cloud_off_outlined,
                size: 64, color: Colors.white),
          ),
          const SizedBox(height: 24),
          const Text(
            'Serviço temporariamente indisponível',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Não foi possível conectar ao servidor de análise. '
            'Verifique sua conexão e tente novamente em instantes.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
          const SizedBox(height: 32),
          OutlinedButton.icon(
            onPressed: _checkHealth,
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: const BorderSide(color: Colors.white70),
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
            icon: const Icon(Icons.refresh),
            label: const Text('Tentar novamente'),
          ),
        ],
      ),
    );
  }
}
