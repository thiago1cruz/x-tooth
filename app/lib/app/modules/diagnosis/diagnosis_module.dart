import 'package:flutter_modular/flutter_modular.dart';

import '../../core/client/i_client_http.dart';
import '../../core/core_module.dart';
import 'data/repositories/diagnosis_repository_impl.dart';
import 'domain/repositories/i_diagnosis_repository.dart';
import 'ui/pages/diagnosis_page.dart';
import 'viewmodel/diagnosis_viewmodel.dart';

class DiagnosisModule extends Module {
  @override
  List<Module> get imports => [CoreModule()];

  @override
  void binds(Injector i) {
    i.addLazySingleton<IDiagnosisRepository>(
        () => DiagnosisRepositoryImpl(i.get<IClientHttp>()));
    i.addLazySingleton<DiagnosisViewmodel>(
        () => DiagnosisViewmodel(i.get<IDiagnosisRepository>()));
  }

  @override
  void routes(RouteManager r) {
    r.child('/', child: (_) => const DiagnosisPage());
  }
}
