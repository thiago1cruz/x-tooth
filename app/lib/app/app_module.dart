import 'package:flutter_modular/flutter_modular.dart';

import 'core/core_module.dart';
import 'core/ui/splash/splash_page.dart';
import 'modules/diagnosis/diagnosis_module.dart';

class AppModule extends Module {
  @override
  List<Module> get imports => [CoreModule()];

  @override
  void routes(RouteManager r) {
    r.child('/', child: (_) => const SplashPage());
    r.module('/diagnosis', module: DiagnosisModule());
  }
}
