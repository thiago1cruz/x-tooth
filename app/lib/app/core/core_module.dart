import 'package:flutter_modular/flutter_modular.dart';

import 'client/i_client_http.dart';
import 'client/rest_client_dio_impl.dart';

/// Binds compartilhados por todo o app.
class CoreModule extends Module {
  @override
  void exportedBinds(Injector i) {
    i.addSingleton<IClientHttp>(RestClientDioImpl.new);
  }
}
