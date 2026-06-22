# 14 · Implementation Backlog Final

## 1. Objetivo del documento

Este documento resume el estado real del proyecto **Sistema de Subastas** al revisar el código actual de `backend-da1` y el repo hermano `frontend-da1`. Lista los pendientes necesarios para llegar a una entrega final funcional, trazable y alineada con la consigna del TPO.

Se conserva el nombre `14_IMPLEMENTATION_BACKLOG_FINAL.md` porque la carpeta `context/` ya usa numeración secuencial y `README.md` enumera documentos del 00 al 13. Este archivo funciona como el siguiente documento de contexto técnico.

Regla usada para clasificar estado:

- Para estado actual gana el código real.
- Para requisitos esperados ganan `context/TPO_DAI_1C2026.md` y `docs/Swagger_v4.YAML`.
- Si Swagger, frontend y backend no coinciden, se documenta la desalineación.
- Si no se puede confirmar, queda marcado como `PENDIENTE DE CONFIRMAR`.

## 2. Alcance analizado

### Backend

- `main.py`
- `app/config.py`
- `app/dependencies.py`
- `app/core/security.py`
- `app/api/router.py`
- `app/api/auth.py`
- `app/api/admin.py`
- `app/api/usuarios.py`
- `app/api/subastas.py`
- `app/api/articulos.py`
- `app/api/notificaciones.py`
- `app/api/uploads.py`
- `app/api/paises.py`
- `app/services/auth_service.py`
- `app/services/admin_service.py`
- `app/services/usuario_service.py`
- `app/services/subasta_service.py`
- `app/services/articulo_service.py`
- `app/services/streamer.py`
- `app/services/email_service.py`
- `app/services/storage_service.py`
- `app/repositories/usuario_repo.py`
- `app/repositories/subasta_repo.py`
- `app/repositories/articulo_repo.py`
- `app/repositories/puja_repo.py`

### Frontend

- `../frontend-da1/context/`
- `../frontend-da1/context/specs/`
- `../frontend-da1/context/progress-tracker.md`
- `../frontend-da1/src/services/api.ts`
- `../frontend-da1/src/services/authService.ts`
- `../frontend-da1/src/services/userService.ts`
- `../frontend-da1/src/services/auctionService.ts`
- `../frontend-da1/src/services/articleService.ts`
- `../frontend-da1/src/types/`
- `../frontend-da1/src/context/AuthContext.tsx`
- `../frontend-da1/app/(auth)/`
- `../frontend-da1/app/(tabs)/`
- `../frontend-da1/app/subasta/[id]/index.tsx`
- `../frontend-da1/app/consignar.tsx`
- `../frontend-da1/package.json`
- `../frontend-da1/.env` solo para verificar variable usada, sin copiar secretos.

### Context/documentación

- `context/README.md`
- `context/00_OVERVIEW.md`
- `context/01_ARCHITECTURE.md`
- `context/04_AI_WORKFLOW.md`
- `context/06_TESTING_AND_VALIDATION.md`
- `context/07_DOMAIN_NOTES.md`
- `context/08_PENDING_CONTEXT.md`
- `context/10_API_REFERENCE.md`
- `context/11_DATABASE.md`
- `context/12_INTEGRATION.md`
- `context/13_SECURITY.md`
- `context/TPO_DAI_1C2026.md`

### Swagger/API contract

- `docs/Swagger_v4.YAML`
- `frontend-da1/context/Swagger_v4.YAML` se consideró copia del contrato, no fuente primaria.

### Base de datos

- `db/Estructura-PostgreSQL-da1-updated.sql`
- `db/seed_subastas_demo.sql`
- `db/rollback_seed_subastas_demo.sql`

### Tests

- `tests/test_usuarios.py`
- `tests/test_flow_articulo_producto.py`
- `tests/test_email.py`
- Búsqueda de tests frontend fuera de `node_modules`: no se encontraron archivos de test/spec.

Validación ejecutada:

- `.venv/bin/python -m unittest discover -s tests -v`: no terminó limpio. Falló el test de integración real de email por DNS/red y luego el proceso quedó colgado en `tests.test_usuarios`.
- `.venv/bin/python -m unittest tests.test_flow_articulo_producto tests.test_usuarios ... -v` excluyendo el envío real de email: los tests de artículo/producto pasaron, pero volvió a colgar al entrar en `tests.test_usuarios`.
- `node --version`: `node` no está instalado en este entorno, por lo que no se pudo correr lint/build del frontend.

## 3. Estado general del proyecto

El proyecto tiene una base bastante sólida en backend: FastAPI está organizado en routers, services y repositories; el esquema PostgreSQL cubre las entidades principales; existen JWT, blacklist de logout, perfil, medios de pago, subastas, join, pujas con `SELECT ... FOR UPDATE`, cierre, pagos, multas, notificaciones y consignación de artículos.

Lo más avanzado del backend está en:

- Auth/login/logout y reset de contraseña.
- Perfil y medios de pago.
- Consignación: publicación, evaluación admin de artículo, aceptación de tasación, creación de seguro/producto y aumento de seguro.
- Subastas: listados, detalle público/autenticado, join/leave, pujas, historial, cierre manual, generación de pagos y SSE básico.

El frontend también está avanzado para una demo:

- Registro paso 1 y 2.
- Login con feedback claro.
- Recuperación de contraseña separada de registro/medios de pago.
- Home, listado de subastas, detalle de subasta y pantalla live.
- Perfil con edición, medios de pago, métricas, multas y notificaciones.
- Pantalla de consignación para publicar artículos.

Lo que está parcialmente conectado:

- Front consume endpoints reales de auth, perfil, medios, subastas, join, pujas, historial, artículos y notificaciones.
- `auctionService` tiene métodos para crear subastas, agregar items y pagar subastas, pero no hay pantallas admin ni pantalla de pago conectadas.
- `articleService` tiene métodos para aceptar tasación y aumentar seguro, pero no hay pantalla que los use.
- `userService` tiene `pagarMulta`, pero la pantalla de perfil sólo lista multas; no ofrece acción de pago.

Lo que impide considerar el sistema 100% funcional y seguro:

- El registro se auto-aprueba en `/auth/registro/paso1`, contradiciendo la consigna y Swagger.
- Varios endpoints `/admin/*` y `/subastas/{id}/cerrar` sólo piden token, no admin.
- El backend ignora `Idempotency-Key`, aunque Swagger lo define y el frontend lo envía.
- El frontend no consume SSE; la pantalla live no se actualiza con pujas de otros usuarios.
- El cierre/pago/multa no cubre la cadena completa de incumplimiento, fondos insuficientes, multa 10%, bloqueo y vencimientos.
- No hay UI admin.
- No hay UI de pago de subasta.
- No hay UI completa para seguimiento de artículos consignados, aceptación de tasación o aumento de seguro.
- El frontend actual apunta en `.env` a `http://localhost:8000`; para entrega en dispositivo debe revisarse contra backend online.
- La suite automatizada es parcial y hoy no termina limpia en este entorno.

Riesgos principales:

- Seguridad: usuarios comunes pueden ejecutar acciones administrativas.
- Trazabilidad: Swagger promete comportamiento que el código no cumple en registro, admin, idempotencia, cierre y listados abiertos.
- Tiempo real: SSE existe en backend pero no hay cliente real.
- Negocio: moneda de subasta está en Swagger/modelos pero no existe en `subastas` del SQL; el backend hardcodea `USD`.
- Datos: listados públicos/autenticados no filtran explícitamente `estado='abierta'`.
- Tests insuficientes para pujas, pagos, admin, SSE, cierre, multas y frontend.

## 4. Mapa de funcionalidades

| Flujo / módulo | Estado | Backend | Frontend | DB / Swagger | Riesgo | Prioridad |
|---|---|---|---|---|---|---|
| Registro paso 1 / paso 2 | Parcial | Paso 1 crea pendiente pero llama `aprobar_registro` de inmediato; paso 2 setea password y medio inicial opcional. | Pantallas `register-step1` y `register-step2` consumen API. | Swagger dice que paso 1 queda pendiente. DB soporta pendiente/aprobado/rechazado. | Alto: incumple consigna y deja sin sentido la verificación admin. | P0 |
| Login / logout / reset password | Implementado | Login valida password, aprobado, admitido y bloqueado; logout blacklistea `jti`; forgot/reset usan `token_email`. `/verify-email` es stub. | Login, forgot y reset implementados. | Swagger incluye verify-email, pero backend no lo implementa. | Medio: verify-email inconsistente; reset token no tiene expiración confirmada. | P1 |
| Verificación de usuario por admin | Parcial | `/admin/usuarios/{id}/verificar` aprueba/rechaza y envía email, pero no llama `_require_admin`. | No hay UI admin. | Swagger exige 403 sólo administradores. DB soporta estados. | Alto: endpoint admin abierto a cualquier autenticado. | P0 |
| Perfil de usuario | Implementado | `GET/PATCH /usuarios/me`, borrar foto y métricas existen. | Perfil muestra/edita datos y foto. | Swagger y schemas cubren campos principales. | Bajo/medio: SQL inline en router; tests colgados. | P1 |
| Medios de pago | Parcial | CRUD de medios existe; guarda `datos_encriptados` sin cifrado verificable. | Perfil lista/agrega/elimina medios. | DB soporta tipo, moneda, límite, cuenta receptora. | Medio: no hay cifrado real ni validación fuerte de datos. | P1 |
| Verificación de medios de pago | Parcial | `/admin/medios-pago/{id}/verificar` existe pero sin `_require_admin`. | No hay UI admin de verificación. | Swagger exige admin. | Alto: acción administrativa abierta. | P0 |
| Listado de subastas públicas | Parcial | `/subastas/publicas` existe, pero no filtra `estado='abierta'`. | Home/Subastas consumen público si no hay login. | Swagger dice subastas abiertas. DB tiene estado. | Medio: puede mostrar cerradas como públicas. | P1 |
| Listado de subastas autenticadas | Parcial | `/subastas` existe y reutiliza públicas; no filtra por acceso/categoría. | Subastas consume autenticado si hay token. | Swagger espera disponibles/autorizadas. | Medio: listado no representa elegibilidad real. | P1 |
| Detalle de subasta | Parcial | Público oculta `precioBase`; autenticado muestra catálogo/precios. No valida acceso por categoría. | Pantalla detalle consume público/autenticado. | `subastado` está desalineado: TS espera `'no'`, backend devuelve `false` para no vendido. | Medio: acceso y tipos pueden romper UI sutilmente. | P1 |
| Join / salir de subasta | Parcial | Join valida categoría, medio validado, multa/bloqueo y otra sesión. Leave actualiza sesión. | Live permite unirse/salir. | Swagger documenta join y delete `/join`; spec vieja decía delete `/subastas/{id}` pero código usa `/join`. | Medio: no hay tests y leave no confirma si actualizó algo. | P1 |
| Streaming SSE / pantalla en vivo | Parcial | `/subastas/{id}/stream` existe con keepalive y broadcast en memoria. Sólo valida JWT, no acceso a la subasta. | Live no usa `EventSource`; actualiza local tras pujar. | Swagger define SSE. Spec pide eventos `puja`/`item`; backend emite `puja`/`cierre`. | Alto: requisito de tiempo real no cumplido end-to-end. | P0 |
| Motor de pujas | Parcial | Valida unido, lock `FOR UPDATE`, 1%/20%, premium oro/platino y registra puja. | Live permite puja rápida/custom. | Swagger define `Idempotency-Key`. DB registra `pujos`. | Alto: sin idempotencia, sin garantía/límite reservado, moneda hardcodeada. | P0 |
| Idempotencia / doble tap de pujas | Pendiente | No lee header ni deduplica. | Front envía `Idempotency-Key` con `Date.now()`. | Swagger lo define. No hay tabla/columna para claves. | Alto: doble tap/reintento puede duplicar pujas. | P0 |
| Cierre de subasta | Parcial | `/subastas/{id}/cerrar` cierra manual, marca ganadores, genera pagos y notifica, pero no valida admin. | No hay UI admin de cierre. | Swagger dice sólo empresa/admin. | Alto: cualquier usuario autenticado puede cerrar. | P0 |
| Generación de pagos | Parcial | Se generan pagos en cierre para clientes con pujas ganadoras. | No hay pantalla de deuda/pago. | DB soporta pagos. Swagger cubre GET/POST pagos. | Alto/medio: sin UI y con reglas incompletas de no pujas/empresa. | P0 |
| Pago de subasta | Parcial | `GET/POST /pagos` existe. `POST` sólo verifica que el usuario tenga algún medio validado, no que el `medioPagoId` enviado le pertenezca/esté validado/moneda coincida. | Servicio existe, UI no lo usa. | Swagger espera fondos insuficientes/moneda inválida. | Alto: bug de autorización y negocio. | P0 |
| Costo de envío | Parcial | Si `modo_entrega='envio'`, usa costo fijo 500. | No hay UI de pago/envío. | DB tiene `costo_envio`. Consigna pide costo de envío. | Medio: fórmula `PENDIENTE DE CONFIRMAR`. | P1 |
| Retiro y pérdida de seguro | Parcial | Backend fuerza `acepta_perder_seguro=true` si retiro. | No hay UI de pago/retiro. | DB tiene `acepta_perder_seguro`. | Medio: falta consentimiento visible en UI. | P1 |
| Multas | Parcial | `GET /multas` y `POST /multas/pagar` existen. `generar_multa` existe pero no se invoca. | Perfil lista multas; no hay botón para pagar. | DB soporta multas. TPO exige multa 10%. | Alto: incumplimiento de pago no dispara multa. | P0 |
| Bloqueo de usuario | Parcial | Join consulta `multa_activa`/`bloqueado`. `bloquear_usuario` existe pero no se invoca. Login rechaza bloqueado. | Perfil muestra alerta si `multaActiva`. | DB soporta flags. | Alto: no hay flujo automático de bloqueo por vencimiento. | P0 |
| Límite por garantía / cheque certificado | Pendiente | No se valida `medios_pago.limite_reservado` al pujar/pagar. | UI permite cargar límite. | DB tiene `limite_reservado`. TPO lo exige. | Medio/alto: regla central de garantía ausente. | P1 |
| Métricas de usuario | Parcial | `/usuarios/me/metricas` calcula participación, ganadas, pujas, montos, categorías. | Perfil muestra métricas. | Swagger cubre `UsuarioMetricas`. | Medio: no distingue bien "mis subastas"; sin tests. | P1 |
| Notificaciones | Parcial | Listar/marcar leída y creación en algunos flujos. | Perfil muestra y marca leídas. | DB y Swagger cubren notificaciones. | Medio: sin push, sin cobertura de todos los eventos esperados. | P1 |
| Consignación de artículos | Parcial | `POST /articulos`, list/detalle, validaciones y storage existen. | `consignar.tsx` publica artículo. | DB y Swagger soportan artículos. | Medio: UI no lista publicaciones reales ni estados. | P1 |
| Evaluación admin de artículos | Parcial | Backend protegido con `_require_admin` sólo para este endpoint. | No hay UI admin. | Swagger cubre evaluación. | Medio: funcional por API, no por app. | P1 |
| Aceptación/rechazo de tasación | Parcial | Backend existe y cambia estado/devuelto o crea seguro/producto. | `articleService` existe, sin pantalla. | DB soporta `tasacion_aceptada`, `seguros`, `productos`. | Medio: flujo no usable desde app. | P1 |
| Conversión de artículo a producto | Parcial | Backend crea seguro/producto/fotos al aceptar tasación; también puede convertir al agregar catálogo desde artículo. | Sin UI de aceptación/admin catálogo. | DB soporta productos/fotos_adicionales. | Medio: riesgo de producto duplicado si no se define camino único. | P1 |
| Seguro / póliza / aumento de seguro | Parcial | Seguro se crea al aceptar tasación; aumento existe. | Servicio existe, sin pantalla. | DB soporta seguros. | Medio: no hay UX de ver póliza/aumentar seguro. | P1 |
| Subasta tipo colección | Pendiente | No hay modelo/flag/endpoint específico. | No hay UI. | No se ve columna específica. | Bajo/medio: puede quedar fuera de alcance si se documenta. | P2 |
| Creación de subastas y catálogo por admin | Parcial | Endpoints existen, sin `_require_admin`; crean catálogo e items. Moneda se recibe pero no se persiste en `subastas`. | Servicios TS existen, no hay UI admin. | Swagger incluye `moneda`; DB `subastas` no tiene columna moneda. | Alto: admin abierto y contrato/DB desalineados. | P0 |
| Seguridad / permisos admin | Parcial | JWT/blacklist OK. Admin hardcodeado ID 1. Muchos endpoints admin sin guard. CORS abierto. | No hay separación UI admin. | Swagger exige admin. DB no modela rol API. | Alto. | P0 |
| Deploy / variables de entorno / secretos | Parcial | Docker/Render documentado. `.env` no está trackeado. `SECRET_KEY` tiene default inseguro. | `.env` local apunta a `http://localhost:8000`; prod está comentado. | Tercera entrega exige backend online y front instalable. | Medio/alto antes de entrega. | P0 |
| Tests automatizados | Parcial | 3 archivos de tests, cobertura baja. Suite no terminó limpia en este entorno. | No hay tests frontend fuera de `node_modules`; `node` no disponible. | No hay coverage/lint Python. | Alto para cambios restantes. | P1 |

## 5. Pendientes priorizados

### P0 — Bloqueantes para entrega final

#### P0.1 — Desacoplar auto-aprobación del registro

* Estado actual: `/auth/registro/paso1` crea el usuario pendiente y luego llama inmediatamente a `UsuarioRepository.aprobar_registro`, setea `admitido='si'`, `estado_registro='aprobado'` y envía token.
* Evidencia encontrada: `app/api/auth.py:registro_paso1`, `app/repositories/usuario_repo.py:aprobar_registro`, `context/07_DOMAIN_NOTES.md`, `docs/Swagger_v4.YAML` describe paso 1 como pendiente de verificación.
* Por qué falta: la consigna exige verificación externa por la empresa antes de asignar categoría y habilitar paso 2. El flujo actual saltea esa revisión.
* Fuente de verdad: `context/TPO_DAI_1C2026.md`, `docs/Swagger_v4.YAML`, `db/Estructura-PostgreSQL-da1-updated.sql`.
* Archivos involucrados: `app/api/auth.py`, `app/api/admin.py`, `app/repositories/usuario_repo.py`, `app/services/email_service.py`, `frontend-da1/app/(auth)/register-step1.tsx`, `frontend-da1/app/(auth)/register-step2.tsx`.
* Forma correcta de implementarlo: dejar paso 1 en `pendiente` y mover el envío del token de paso 2 exclusivamente al endpoint admin de aprobación. El rechazo debe quedar con `estado_registro='rechazado'`, `admitido='no'` y motivo.
* Cambios backend: quitar llamada a `aprobar_registro` de `registro_paso1`; devolver mensaje de solicitud recibida; asegurar que `/admin/usuarios/{id}/verificar` sólo lo pueda ejecutar admin.
* Cambios frontend: ajustar texto post-registro para decir "solicitud enviada, pendiente de revisión"; no prometer código inmediato. Mantener acceso manual a paso 2 para cuando llegue email.
* Cambios DB / migración si aplica: no parece requerir migración; DB ya soporta estados.
* Tests recomendados: paso 1 deja `pendiente`; login de pendiente devuelve 403; admin aprueba y genera token; admin rechaza y bloquea paso 2; usuario no admin no puede aprobar.
* Riesgos: romper demo si hoy depende del auto-token. Conviene tener usuario aprobado/seed para pruebas.
* Dependencias: P0.2 porque el endpoint admin debe estar protegido antes de usarlo como flujo real.
* Spec sugerida: `context/specs/13-admin-registration-verification.md`.

#### P0.2 — Proteger todos los endpoints admin y el cierre de subasta

* Estado actual: `_require_admin` existe pero sólo se usa en `/admin/articulos/{id}/evaluar`. No se usa en verificar usuarios, verificar medios, crear subasta, agregar item ni cerrar subasta.
* Evidencia encontrada: `app/api/admin.py`, `app/api/subastas.py:close_auction`, `context/10_API_REFERENCE.md`, `docs/Swagger_v4.YAML`.
* Por qué falta: Swagger y la consigna asumen acciones de empresa/admin; el código permite que cualquier usuario autenticado las ejecute.
* Fuente de verdad: `docs/Swagger_v4.YAML` y `context/13_SECURITY.md`.
* Archivos involucrados: `app/api/admin.py`, `app/api/subastas.py`, `app/dependencies.py`, opcionalmente `app/repositories/usuario_repo.py`.
* Forma correcta de implementarlo: aplicar un guard admin consistente en cada ruta administrativa y en `/subastas/{id}/cerrar`. Mantener `usuarioId == 1` si no hay decisión de rol real, pero centralizarlo.
* Cambios backend: llamar `_require_admin(user)` en endpoints faltantes; idealmente moverlo a una dependencia `require_admin`.
* Cambios frontend: si luego se crea UI admin, ocultarla/impedirla para usuarios no admin.
* Cambios DB / migración si aplica: no obligatoria si se mantiene ID 1. Si se decide rol real, requiere modelado.
* Tests recomendados: cada endpoint admin devuelve 403 para usuario común y permite admin ID 1.
* Riesgos: si en producción el admin no es ID 1, se bloquea operación. Confirmar admin real antes de entrega.
* Dependencias: decisión del equipo sobre modelo de admin.
* Spec sugerida: `context/specs/13-admin-registration-verification.md`.

#### P0.3 — Implementar idempotencia real de pujas y cerrar el doble tap

* Estado actual: Swagger define header `Idempotency-Key`; frontend lo envía en `auctionService.pujar`; backend no lo recibe ni persiste. El lock `FOR UPDATE` serializa concurrencia sobre el item, pero no deduplica reintentos.
* Evidencia encontrada: `docs/Swagger_v4.YAML` en `/subastas/{id}/items/{itemId}/pujar`; `frontend-da1/src/services/auctionService.ts`; `app/api/subastas.py:place_bid`; `app/services/subasta_service.py:procesar_puja`; `app/repositories/puja_repo.py` está vacío.
* Por qué falta: doble tap, retry de red o reenvío puede crear dos pujas válidas si ambas cumplen los límites después de la primera.
* Fuente de verdad: consigna TPO sobre no permitir otra puja hasta confirmación, Swagger y spec 07.
* Archivos involucrados: `app/api/subastas.py`, `app/services/subasta_service.py`, `app/repositories/subasta_repo.py` o `app/repositories/puja_repo.py`, `db/`, `frontend-da1/app/(tabs)/live.tsx`.
* Forma correcta de implementarlo: leer `Idempotency-Key` en router, registrar clave por usuario/subasta/item en una tabla o mecanismo transaccional, devolver la misma respuesta ante reintento con la misma clave y rechazar conflictos.
* Cambios backend: agregar header opcional en `place_bid`; service valida/deduplica dentro de la misma transacción; repositorio persiste clave y resultado o estado.
* Cambios frontend: deshabilitar botones mientras `sending=true` ya existe; generar clave estable por intento, no sólo `Date.now()` en el momento de llamar si se necesita retry.
* Cambios DB / migración si aplica: probablemente nueva tabla `puja_idempotency_keys` o columna equivalente. `PENDIENTE DE CONFIRMAR` porque el schema actual no la tiene.
* Tests recomendados: dos requests con misma key devuelven una sola puja; dos keys distintas compiten por reglas normales; request sin key sigue funcionando si Swagger lo mantiene opcional.
* Riesgos: si se implementa mal puede bloquear pujas legítimas o romper concurrencia.
* Dependencias: definir migraciones.
* Spec sugerida: `context/specs/14-realtime-puja-idempotency.md`.

#### P0.4 — Conectar SSE end-to-end y validar acceso al stream

* Estado actual: backend expone SSE y broadcast de pujas/cierre, pero el frontend no abre conexión SSE. El endpoint sólo valida token, no join/categoría/medio/sesión. `SubastaStreamer` vive en memoria.
* Evidencia encontrada: `app/api/subastas.py:stream_auction`, `app/services/streamer.py`, `frontend-da1/app/(tabs)/live.tsx`, `frontend-da1/src/types/common.ts`, spec 08.
* Por qué falta: la consigna exige que usuarios conectados reciban ofertas en tiempo real; hoy sólo ve cambios locales y carga historial puntual.
* Fuente de verdad: `context/TPO_DAI_1C2026.md`, `docs/Swagger_v4.YAML`, `frontend-da1/context/specs/08-streaming-sse.md`.
* Archivos involucrados: `app/api/subastas.py`, `app/services/subasta_service.py`, `app/repositories/subasta_repo.py`, `app/services/streamer.py`, `frontend-da1/app/(tabs)/live.tsx`, posible dependencia frontend para SSE en React Native.
* Forma correcta de implementarlo: validar que el usuario puede ver/participar en la subasta antes de suscribir; en frontend abrir SSE al unirse, actualizar item/historial ante evento y cerrar conexión al salir.
* Cambios backend: agregar `db` al endpoint de stream; validar subasta abierta, categoría, sesión activa o al menos acceso permitido; documentar mono-worker.
* Cambios frontend: elegir cliente SSE compatible con Expo/React Native o fallback polling si no se acepta dependencia; manejar reconexión, cierre y cleanup.
* Cambios DB / migración si aplica: no requiere migración.
* Tests recomendados: stream rechaza usuario sin acceso; broadcast de puja llega a listener; cleanup al desconectar; UI actualiza con evento simulado.
* Riesgos: Render multi-worker rompe broadcast en memoria. Confirmar un solo worker.
* Dependencias: decisión sobre librería SSE frontend.
* Spec sugerida: `context/specs/14-realtime-puja-idempotency.md`.

#### P0.5 — Corregir cierre, generación de deuda y pago de subasta

* Estado actual: cierre manual genera pagos para ganadores y notifica; no valida admin. Pago existe, pero no valida que `medioPagoId` pertenezca al usuario, esté validado, tenga moneda compatible o fondos suficientes. El frontend no tiene pantalla de resumen/pago.
* Evidencia encontrada: `app/services/subasta_service.py:cerrar_subasta`, `app/repositories/subasta_repo.py:generar_pago`, `get_pago_usuario`, `confirmar_pago`; `frontend-da1/src/services/auctionService.ts` tiene métodos sin uso en pantallas.
* Por qué falta: la compra, deuda, envío/retiro, moneda y pago son parte central del flujo post-subasta.
* Fuente de verdad: TPO, Swagger `/subastas/{id}/cerrar` y `/subastas/{id}/pagos`.
* Archivos involucrados: `app/api/subastas.py`, `app/services/subasta_service.py`, `app/repositories/subasta_repo.py`, `frontend-da1/app/(tabs)/profile.tsx` o nueva pantalla de pago.
* Forma correcta de implementarlo: cerrar sólo como admin; generar deuda completa; validar pago contra el medio específico del usuario; exponer UI de deuda y confirmación.
* Cambios backend: proteger cierre; validar `medio_pago_id` con `cliente_id`, `estado_verificacion='validado'`, moneda y límite; definir qué ocurre con items sin pujas y compra por empresa.
* Cambios frontend: pantalla o sección de pagos pendientes; seleccionar medio validado; elegir envío/retiro; confirmar pérdida de seguro si retiro.
* Cambios DB / migración si aplica: no necesariamente, salvo si se persiste moneda real de subasta.
* Tests recomendados: usuario común no cierra; cierre genera pagos correctos; pago con medio ajeno devuelve 403/404; pago con medio no validado falla; retiro fuerza seguro; envío calcula costo.
* Riesgos: la DB no tiene moneda en `subastas`; hoy todo se guarda como `USD`.
* Dependencias: decidir moneda real y costo de envío.
* Spec sugerida: `context/specs/15-pagos-multas-vencimientos.md`.

#### P0.6 — Implementar flujo de multas, vencimientos y bloqueo

* Estado actual actualizado 2026-06-21: backend implementado con endpoint manual `POST /admin/pagos/procesar-vencimientos`, validacion lazy y pago de multas en service/repository. Frontend de pago de multas queda pendiente porque el entorno de esta corrida bloqueo escritura en `../frontend-da1`.
* Evidencia encontrada/actualizada: `app/repositories/subasta_repo.py:generar_multa`, `get_pagos_pendientes_vencidos`, `marcar_pago_vencido`, `bloquear_usuario`; `app/services/subasta_service.py:procesar_vencimientos`, `join_subasta`, `procesar_puja`; `app/services/usuario_service.py:pagar_multa`; `app/api/admin.py:process_overdue_payments`.
* Por qué faltaba: TPO exige multa del 10%, pago antes de participar, 72 hs para presentar fondos y bloqueo por incumplimiento.
* Fuente de verdad: `context/TPO_DAI_1C2026.md`, spec 10.
* Archivos involucrados: `app/services/subasta_service.py`, `app/repositories/subasta_repo.py`, `app/api/usuarios.py`, posible endpoint/admin job nuevo, `frontend-da1/app/(tabs)/profile.tsx`.
* Forma implementada: endpoint admin manual + validacion lazy en join/stream/puja/consulta de pago/listar o pagar multas. Aplica multa al pago vencido/no pagado y bloquea si vence la multa pendiente.
* Cambios backend: consulta de pagos vencidos; creación de multa 10%; set `multa_activa`; bloqueo por multa vencida; duplicados evitados con `motivo` deterministico.
* Cambios frontend: PENDIENTE por bloqueo de escritura en esta corrida. Sigue faltando CTA/selector de medio validado en perfil.
* Cambios DB / migración si aplica: no se hizo migracion; queda PENDIENTE DE CONFIRMAR si se agrega `multas.pago_id`.
* Tests agregados/ejecutados: `tests/test_subasta_multas.py`; pago vencido genera una sola multa; multa pendiente bloquea join; pagar multa limpia `multa_activa`; usuario bloqueado no loguea.
* Riesgos: sin scheduler en Render, el flujo automatico depende de endpoint manual y lazy triggers.
* Dependencias: confirmar migracion robusta, scheduler y regla final de bloqueo fuerte.
* Spec sugerida: `context/specs/15-pagos-multas-vencimientos.md`.

#### P0.7 — Preparar deploy real de entrega y variables de entorno

* Estado actual: backend documenta Render y Docker; frontend `.env` actual apunta a `http://localhost:8000` con prod comentado. `.env` no está trackeado en ambos repos. `SECRET_KEY` tiene default inseguro si no se setea.
* Evidencia encontrada: `main.py`, `app/config.py`, `Dockerfile`, `context/13_SECURITY.md`, `frontend-da1/.env`, `frontend-da1/package.json`.
* Por qué falta: tercera entrega exige backend accesible online y front instalable/probable en dispositivo.
* Fuente de verdad: entregables del TPO.
* Archivos involucrados: config de Render, `.env` local/prod, `app/config.py`, frontend Expo env.
* Forma correcta de implementarlo: confirmar variables en Render, rotar secretos si circularon, setear `EXPO_PUBLIC_API_URL` de producción para build/dispositivo, mantener `.env` fuera de git.
* Cambios backend: no necesariamente código; sí configuración y checklist.
* Cambios frontend: configurar env de producción o perfil de build.
* Cambios DB / migración si aplica: confirmar mecanismo de migraciones antes de tocar esquema.
* Tests recomendados: smoke contra backend online; login en dispositivo/emulador; `/docs`; flujo auth + subasta.
* Riesgos: CORS abierto, secret default, credenciales compartidas fuera de repo.
* Dependencias: acceso a Render/Supabase/Expo.
* Spec sugerida: `context/specs/18-deploy-release-hardening.md`.

### P1 — Importantes pero no bloqueantes

#### P1.1 — Alinear listados/detalles de subastas con Swagger y frontend

* Estado P1.1: implementado en `feature/p1-1-auction-listings-details`. Ver `context/20_P1_1_AUCTION_LISTINGS_DETAILS_NOTES.md`.
* Estado anterior: listados no filtraban explícitamente abiertas; detalle autenticado no validaba acceso por categoría; moneda se hardcodeaba como `USD`; `subastado` volvía como `false` para no vendido aunque TS esperaba `'no'`.
* Evidencia encontrada: `app/repositories/subasta_repo.py:get_publicas`, `get_detalle`, `schemas.py:Subastado`, `frontend-da1/src/types/auction.ts`.
* Por qué falta: contrato y UI esperan semántica estable para públicas/autenticadas.
* Fuente de verdad: Swagger y spec 05.
* Archivos involucrados: `app/repositories/subasta_repo.py`, `app/schemas/schemas.py`, `docs/Swagger_v4.YAML`, `frontend-da1/src/types/auction.ts`, pantallas de subastas.
* Forma correcta de implementarlo: filtrar estado según contrato; definir si autenticado puede ver todas o sólo elegibles; corregir enum `Subastado` o normalizar frontend/backend de forma consistente.
* Cambios backend: queries filtradas por `estado='abierta'` en listados, detalle público abierto, validación de categoría en detalle autenticado, `Subastado` `si/no`.
* Cambios frontend: normalización defensiva en `auctionService` y mensaje claro para `403` de detalle autenticado.
* Cambios DB / migración si aplica: no se migra en P1.1; moneda real por subasta queda en P2.3.
* Tests recomendados: cubiertos por `tests/test_subasta_listados_detalles.py`; ver nota P1.1 para validación ejecutada.
* Riesgos: cambiar response puede romper UI actual.
* Dependencias: PENDIENTE DE CONFIRMAR decisión sobre moneda real por subasta.
* Spec sugerida: spec 05 queda alineada en backend/frontend; tracker frontend actualizado puntualmente.

#### P1.2 — Completar UI admin para usuarios, medios, artículos, subastas y catálogo

* Estado actual: backend y servicios TS tienen varias acciones admin, pero no existen pantallas admin en `app/`.
* Evidencia encontrada: `frontend-da1/src/services/auctionService.ts:createSubasta/addCatalogItem`, `app/api/admin.py`, búsqueda de `createSubasta/addCatalogItem/verificar` sin uso en pantallas.
* Por qué falta: sin UI admin no se puede operar aprobación de usuarios, medios, evaluación de artículos ni carga de subastas desde la app.
* Fuente de verdad: consigna, Swagger y specs.
* Archivos involucrados: frontend `app/`, `src/services`, backend `app/api/admin.py`.
* Forma correcta de implementarlo: crear navegación/admin guardada por rol o ID admin; pantallas simples para pendientes y acciones.
* Cambios backend: primero P0.2.
* Cambios frontend: nuevo módulo admin con listado de usuarios pendientes, medios pendientes, artículos pendientes, creación de subastas y catálogo.
* Cambios DB / migración si aplica: no necesaria salvo rol real.
* Tests recomendados: render de UI por admin/no admin; llamadas correctas; errores 403.
* Riesgos: admin ID 1 no escala.
* Dependencias: modelo de admin.
* Spec sugerida: `context/specs/16-admin-subastas-catalogo.md`.

#### P1.3 — Completar flujo frontend de consignación posterior a publicación

* Estado actual: el usuario puede publicar artículo. No hay pantalla conectada para listar publicaciones reales, ver detalle, aceptar/rechazar tasación ni aumentar seguro.
* Evidencia encontrada: `frontend-da1/app/consignar.tsx` usa `articleService.publicar`; `articleService` tiene métodos no usados; `profile.tsx` no usa `articleService.getMisPublicaciones`.
* Por qué falta: la consigna exige seguimiento del artículo, causas de rechazo, aceptación de valor/comisión y póliza.
* Fuente de verdad: TPO, Swagger, spec 04 y spec 12.
* Archivos involucrados: `frontend-da1/app/(tabs)/profile.tsx`, nuevas pantallas de artículo, `src/services/articleService.ts`.
* Forma correcta de implementarlo: reemplazar o complementar "Mis Subastas" con "Mis Artículos" reales; detalle con estado, precio/comisión, rechazo, seguro, acciones de aceptación/aumento.
* Cambios backend: endpoints ya existen; revisar duplicación producto si se acepta tasación y luego se agrega por artículo.
* Cambios frontend: pantallas de listado/detalle/acciones.
* Cambios DB / migración si aplica: no requerida.
* Tests recomendados: publicar y ver en mis publicaciones; aceptar tasación; rechazar; pedir aumento de seguro.
* Riesgos: sin UI admin, ningún artículo llega aprobado desde la app.
* Dependencias: P1.2.
* Spec sugerida: `context/specs/17-consignacion-post-evaluacion.md`.

#### P1.4 — Implementar pago de multas en frontend

* Estado actual actualizado 2026-06-21: implementado en frontend. Backend permite pagar multa; `userService.pagarMulta` existe; perfil lista multas y ahora permite pagar multas pendientes con medio validado compatible.
* Evidencia encontrada/actualizada: `frontend-da1/src/services/userService.ts`, `frontend-da1/src/types/payment.ts`, `frontend-da1/app/(tabs)/profile.tsx`, `context/20_P1_4_FRONTEND_MULTAS_NOTES.md`.
* Por qué faltaba: el usuario no podia liberarse desde la app aunque el backend lo soportara.
* Fuente de verdad: spec 10.
* Archivos involucrados: `frontend-da1/app/(tabs)/profile.tsx`, `src/services/userService.ts`.
* Forma implementada: accion sobre multas pendientes, selector de medio validado, evaluacion de limite reservado, confirmacion, loading, manejo de errores HTTP y refresh de perfil/multas/medios.
* Cambios backend: sin cambios funcionales; P0.6 ya cubre generacion/pago y validaciones server-side.
* Cambios frontend: boton pagar, selector de medio compatible, mensajes claros sin medios validados, confirmacion y manejo de errores. Bonus fix: etiquetas/listados `EN VIVO` alineados a fecha/hora de la consigna, sin tratar toda subasta `abierta` como vivo.
* Cambios DB / migración si aplica: no requerida.
* Tests recomendados: multa pendiente muestra CTA; multa pagada no muestra CTA; medio no validado o con limite insuficiente aparece incompatible; pago refresca estado y limpia `multaActiva` si era la ultima pendiente.
* Riesgos: validacion automatica frontend pendiente en entorno con Node; el scheduler externo de vencimientos sigue fuera de alcance.
* Dependencias: P0.6.
* Spec sugerida: spec 10 queda alineada con el flujo implementado.

#### P1.5 — Validar límite de garantía / cheque certificado

* Estado actual: DB y UI permiten `limiteReservado`; backend no lo usa para restringir pujas/compras.
* Evidencia encontrada: `db/Estructura-PostgreSQL-da1-updated.sql:medios_pago.limite_reservado`, `frontend-da1/app/(auth)/register-step2.tsx`, `frontend-da1/app/(tabs)/profile.tsx`, `app/services/subasta_service.py`.
* Por qué falta: el TPO dice que las compras no pueden superar la garantía.
* Fuente de verdad: TPO.
* Archivos involucrados: `app/services/subasta_service.py`, `app/repositories/subasta_repo.py`, `app/api/usuarios.py`.
* Forma correcta de implementarlo: definir si el límite se reserva al join, al pujar o al cerrar; calcular compras pendientes más nueva puja contra límites disponibles.
* Cambios backend: consultas de medios certificados/fondos y pagos pendientes; rechazo 400/403 cuando excede.
* Cambios frontend: mostrar límite disponible y deshabilitar pujas que lo exceden.
* Cambios DB / migración si aplica: no necesariamente.
* Tests recomendados: usuario con límite insuficiente no puede pujar/cerrar compra.
* Riesgos: regla ambigua si tiene múltiples medios.
* Dependencias: decisión de negocio.
* Spec sugerida: `context/specs/15-pagos-multas-vencimientos.md`.

#### P1.6 — Fortalecer tests automatizados

* Estado actual: hay tests parciales de perfil, email y artículo/producto. No hay tests de pujas, cierre, pagos, admin, SSE ni frontend. La suite no terminó limpia en este entorno.
* Evidencia encontrada: `tests/`, comandos ejecutados, `frontend-da1/package.json`, ausencia de tests frontend fuera de `node_modules`.
* Por qué falta: los cambios P0 son de alto riesgo y necesitan cobertura.
* Fuente de verdad: `context/06_TESTING_AND_VALIDATION.md`.
* Archivos involucrados: `tests/`, posible setup frontend.
* Forma correcta de implementarlo: agregar tests unittest con DB mockeada para services/repos y TestClient para permisos; resolver/aislar test de email real.
* Cambios backend: tests nuevos; posiblemente marcar integración real de email como opt-in seguro.
* Cambios frontend: agregar lint/build cuando `node` esté disponible; opcional tests de servicios.
* Cambios DB / migración si aplica: no.
* Tests recomendados: admin guard, registro pendiente, idempotencia, join, puja, cierre, pago, multa.
* Riesgos: mocks mal armados pueden ocultar errores SQL.
* Dependencias: entorno con Python/Node estable.
* Spec sugerida: `context/specs/18-deploy-release-hardening.md`.

### P2 — Mejoras / deuda técnica

#### P2.1 — Mover SQL inline de routers a service/repository

* Estado actual: `usuarios.py`, `notificaciones.py` y partes de `auth.py` tienen SQL directo.
* Evidencia encontrada: archivos `app/api/*.py`.
* Forma correcta de implementarlo: no bloquear entrega; al tocar flujos grandes, mover lógica nueva a service/repository y dejar routers delgados.
* Tests recomendados: mantener respuestas actuales.

#### P2.2 — Corregir modelos generados y nombres inconsistentes

* Estado actual: `schemas.py` tiene enums generados como `Estado1`, `Tipo2`, `Subastado.False_ = False`; TS espera otros valores.
* Evidencia encontrada: `app/schemas/schemas.py`, `frontend-da1/src/types/auction.ts`.
* Forma correcta de implementarlo: actualizar Swagger y regenerar modelos Pydantic/TS juntos.
* Tests recomendados: response_model de detalle con item no vendido.

#### P2.3 — Definir moneda real de subasta

* Estado actual: Swagger y `SubastaCreate` incluyen `moneda`, pero `subastas` no tiene columna. Backend hardcodea `USD`.
* Evidencia encontrada: SQL `subastas`, `schemas.py:SubastaCreate`, `subasta_repo.py`.
* Forma correcta de implementarlo: confirmar si se agrega columna/migración o si moneda queda fuera de alcance.
* Tests recomendados: creación/listado/detalle/pagos conservan moneda.

#### P2.4 — Definir subasta colección

* Estado actual: no hay feature específica.
* Forma correcta de implementarlo: confirmar alcance. Si queda fuera, documentarlo explícitamente como no implementado por alcance.
* Tests recomendados: no aplica hasta confirmar.

#### P2.5 — Reemplazar imágenes placeholder por fotos reales del catálogo cuando existan

* Estado actual: listados usan `PLACEHOLDER_IMAGES`; detalle sí muestra fotos del catálogo cuando backend las devuelve.
* Forma correcta de implementarlo: si el listado necesita imagen principal, extender response o usar detalle/cache.
* Tests recomendados: render sin imagen y con imagen real.

#### P2.6 — Observabilidad y migraciones

* Estado actual: `sentry-sdk` está en requirements, pero no se vio inicialización. `docs/run_migration.py` existe, pero el proceso oficial no está confirmado.
* Forma correcta de implementarlo: confirmar con equipo antes de sumar cambios.
* Tests recomendados: smoke de startup con env de prod.

## 6. Orden recomendado de implementación

### Etapa 1 — Seguridad y registro

Objetivo: cerrar agujeros de permisos y hacer que el registro respete la consigna.

Por qué va antes: cualquier UI admin o flujo de aprobación sería inseguro si primero no se protege.

Archivos principales a tocar:

1. `app/api/auth.py`
2. `app/api/admin.py`
3. `app/api/subastas.py`
4. `app/repositories/usuario_repo.py`
5. `frontend-da1/app/(auth)/register-step1.tsx`

Resultado esperado:

1. Paso 1 deja usuario pendiente.
2. Sólo admin puede aprobar/rechazar.
3. Sólo admin puede verificar medios, crear/cargar/cerrar subastas.
4. Mensajes frontend alineados.

Pruebas mínimas:

1. Registro nuevo queda pendiente.
2. Usuario pendiente no loguea.
3. Usuario común recibe 403 en todos los admin endpoints.
4. Admin aprueba y genera token de paso 2.

### Etapa 2 — Motor de pujas y tiempo real

Objetivo: hacer confiable la participación en vivo.

Por qué va antes: pujas y live son el núcleo de la app.

Archivos principales a tocar:

1. `app/api/subastas.py`
2. `app/services/subasta_service.py`
3. `app/repositories/subasta_repo.py`
4. `app/repositories/puja_repo.py`
5. `app/services/streamer.py`
6. `frontend-da1/app/(tabs)/live.tsx`
7. `frontend-da1/src/services/auctionService.ts`

Resultado esperado:

1. Idempotencia real.
2. SSE consumido por frontend.
3. Stream valida acceso.
4. UI refleja pujas de otros usuarios.

Pruebas mínimas:

1. Doble envío con misma key no duplica.
2. Dos clientes conectados ven broadcast.
3. Usuario sin join/acceso no entra al stream.

### Etapa 3 — Cierre, pagos, multas y bloqueos

Objetivo: completar el ciclo de negocio desde ganador hasta pago o sanción.

Por qué va antes que admin UI extensa: sin reglas backend correctas, la UI sólo decoraría flujos incompletos.

Archivos principales a tocar:

1. `app/services/subasta_service.py`
2. `app/repositories/subasta_repo.py`
3. `app/api/subastas.py`
4. `app/api/usuarios.py`
5. `frontend-da1/app/(tabs)/profile.tsx`
6. posible nueva pantalla `frontend-da1/app/pagos/[subastaId].tsx`

Resultado esperado:

1. Cierre admin seguro.
2. Pago usa medio propio, validado y compatible.
3. Envío/retiro claro.
4. Multas se generan y se pueden pagar.
5. Bloqueos se aplican.

Pruebas mínimas:

1. Cierre genera pagos.
2. Pago con medio ajeno falla.
3. Multa pendiente bloquea join.
4. Pagar multa libera si no quedan pendientes.

### Etapa 4 — Admin operativo

Objetivo: poder operar el sistema desde la app o una superficie admin mínima.

Por qué va después: depende de seguridad y reglas backend.

Archivos principales a tocar:

1. `frontend-da1/app/`
2. `frontend-da1/src/services/auctionService.ts`
3. `frontend-da1/src/services/userService.ts`
4. `frontend-da1/src/services/articleService.ts`
5. `app/api/admin.py`

Resultado esperado:

1. Admin aprueba/rechaza usuarios.
2. Admin valida medios de pago.
3. Admin evalúa artículos.
4. Admin crea subastas y carga catálogo.
5. Admin cierra subastas.

Pruebas mínimas:

1. UI oculta admin para usuario común.
2. Acciones admin manejan 403/404/400.
3. Artículo aprobado llega a producto/catalogable.

### Etapa 5 — Consignación completa para usuario

Objetivo: que el dueño vea todo el ciclo del artículo.

Por qué va después: necesita evaluación admin operativa.

Archivos principales a tocar:

1. `frontend-da1/app/(tabs)/profile.tsx`
2. nueva pantalla de detalle de artículo
3. `frontend-da1/src/services/articleService.ts`
4. `app/services/articulo_service.py` si aparece incompatibilidad

Resultado esperado:

1. Mis publicaciones reales.
2. Detalle con estado, rechazo, tasación, seguro y ubicación.
3. Aceptar/rechazar tasación.
4. Solicitar aumento de seguro.

Pruebas mínimas:

1. Publicación aparece en lista.
2. Artículo aprobado permite aceptar.
3. Artículo rechazado muestra motivo.
4. Aumento de seguro valida monto mayor.

### Etapa 6 — Release hardening

Objetivo: llegar a entrega final reproducible.

Por qué va al final: consolida los flujos ya cerrados.

Archivos principales a tocar:

1. `context/`
2. configs Render/Expo
3. `tests/`
4. `frontend-da1/package.json` y scripts

Resultado esperado:

1. Backend online con secretos seguros.
2. Front apuntando a backend online para dispositivo.
3. Swagger alineado.
4. Tests mínimos pasando.

Pruebas mínimas:

1. Smoke online de auth/perfil/subasta.
2. Suite backend sin hangs.
3. Lint/build frontend en entorno con Node.

## 7. Specs recomendadas

### 13-admin-registration-verification.md

* Nombre sugerido: `13-admin-registration-verification.md`
* Objetivo: cerrar registro pendiente, aprobación/rechazo admin y permisos admin.
* Alcance: backend y ajustes mínimos frontend de registro.
* Endpoints/pantallas involucradas: `/auth/registro/paso1`, `/auth/registro/paso2`, `/admin/usuarios/{id}/verificar`, `/admin/medios-pago/{id}/verificar`, pantallas auth.
* Criterios de aceptación: paso 1 no auto-aprueba; admin aprueba/rechaza; usuario común no ejecuta admin; frontend no promete token inmediato.

### 14-realtime-puja-idempotency.md

* Objetivo: integrar SSE e idempotencia de pujas.
* Alcance: backend pujas/stream y `LiveScreen`.
* Endpoints/pantallas involucradas: `/subastas/{id}/stream`, `/subastas/{id}/items/{item_id}/pujar`, `app/(tabs)/live.tsx`.
* Criterios de aceptación: eventos llegan a otra sesión; doble tap no duplica; stream valida acceso.

### 15-pagos-multas-vencimientos.md

* Objetivo: completar cierre, deuda, pago, costo de envío, retiro, multas y bloqueo.
* Alcance: backend subastas/usuarios y UI de pagos/multas.
* Endpoints/pantallas involucradas: `/subastas/{id}/cerrar`, `/subastas/{id}/pagos`, `/usuarios/me/multas`, perfil/pagos.
* Criterios de aceptación: cierre genera deuda; pago valida medio propio; multa 10% se genera por incumplimiento; multa pendiente bloquea join.

### 16-admin-subastas-catalogo.md

* Objetivo: crear UI admin mínima para operar subastas y catálogo.
* Alcance: frontend admin + endpoints existentes.
* Endpoints/pantallas involucradas: `/admin/subastas`, `/admin/subastas/{id}/catalogo/items`, `/admin/articulos/{id}/evaluar`.
* Criterios de aceptación: admin crea subasta, agrega producto/artículo al catálogo y evalúa consignaciones.

### 17-consignacion-post-evaluacion.md

* Objetivo: completar experiencia del dueño después de publicar.
* Alcance: frontend de mis artículos/detalle/acciones.
* Endpoints/pantallas involucradas: `/articulos/mis-publicaciones`, `/articulos/{id}`, `/articulos/{id}/aceptar-tasacion`, `/articulos/{id}/seguro/aumentar`.
* Criterios de aceptación: usuario ve estado, motivo, tasación, póliza, ubicación y acciones disponibles.

### 18-deploy-release-hardening.md

* Objetivo: preparar entrega final reproducible.
* Alcance: env, deploy, Swagger, tests y smoke tests.
* Endpoints/pantallas involucradas: todos los flujos principales.
* Criterios de aceptación: backend online, front apunta a backend online, tests mínimos pasan, sin secretos commiteados, Swagger actualizado.

## 8. Riesgos y decisiones a confirmar con el equipo

- Si el cierre de subasta debe ser manual, automático por fecha/hora o ambos.
- Cómo se calcula el costo de envío. Hoy es fijo `500.0`.
- Cómo se define un admin real. Hoy es `usuarioId == 1`.
- Si el sistema local externo de la empresa está dentro del alcance real o sólo se representa con la DB existente.
- Si Render corre con un solo worker para SSE.
- Cómo se aplican migraciones en producción. `docs/run_migration.py` existe, pero no está confirmado como proceso oficial.
- Si se espera implementar subasta colección o documentarla como fuera de alcance.
- Si debe persistirse moneda por subasta. Swagger la define, pero el SQL no tiene columna.
- Cómo se modela "empresa compra al precio base" cuando nadie puja: registro, dueño nuevo, pago al consignante o sólo notificación.
- Si `productos.duenio` debe cambiar al ganador o basta con `registrodesubasta`.
- Si el token de reset/verificación debe expirar y ser de un solo uso con auditoría.
- Si los medios de pago necesitan cifrado real/tokenización o alcanza con el campo `datos_encriptados`.
- Si la app debe tener UI admin en móvil o si admin puede operar sólo por Swagger/Postman.

## 9. Checklist de entrega final

- [ ] Backend deployado y accesible.
- [ ] Front instalable en dispositivo y apuntando al backend online.
- [ ] Swagger alineado con endpoints reales.
- [ ] Front consume endpoints reales, sin servicios muertos para flujos críticos.
- [ ] Registro paso 1 queda pendiente y admin aprueba/rechaza.
- [ ] Login/logout/reset funcionan con mensajes claros.
- [ ] Endpoints admin cerrados a usuarios comunes.
- [ ] Medios de pago se pueden crear y verificar por admin.
- [x] Subastas públicas/autenticadas muestran datos correctos y consistentes para P1.1.
- [ ] Join valida categoría, medio verificado, multa/bloqueo y sesión activa.
- [ ] SSE actualiza la pantalla live en tiempo real.
- [ ] Pujas tienen lock e idempotencia.
- [ ] Cierre de subasta sólo admin.
- [ ] Pagos generados y pagables desde la app.
- [ ] Costo de envío definido.
- [ ] Retiro informa pérdida de seguro.
- [/] Multas se generan por incumplimiento y se pueden pagar. Backend P0.6 OK; frontend P1.4 implementado. Scheduler externo sigue fuera de alcance.
- [/] Bloqueos se aplican. Levantamiento automatico de bloqueo fuerte queda PENDIENTE DE CONFIRMAR.
- [ ] Límite por garantía/cheque certificado validado o justificado fuera de alcance.
- [ ] Consignación completa: publicar, ver estado, evaluación, aceptar/rechazar tasación, seguro.
- [ ] Admin puede crear subastas y cargar catálogo.
- [ ] Sin secretos commiteados.
- [ ] `SECRET_KEY` configurado por env en producción.
- [ ] Tests mínimos pasando sin depender de internet.
- [ ] Front lint/build verificado en entorno con Node.
- [ ] Pendientes no implementados justificados como fuera de alcance o `PENDIENTE DE CONFIRMAR`.

## 10. Resumen ejecutivo final

Avance aproximado estimado: **65% a 75%** para una demo integrada; **50% a 60%** para una entrega final segura y trazable al 100%.

Principales bloqueantes:

1. Registro auto-aprobado.
2. Permisos admin incompletos.
3. Pujas sin idempotencia y live sin SSE en frontend.
4. Pago/multa/bloqueo incompleto.
5. Falta UI admin y UI de pago.
6. Tests insuficientes y suite actual no termina limpia en este entorno.

Primer pendiente recomendado para atacar: **P0.2 proteger admin y cierre**, seguido inmediatamente por **P0.1 desacoplar registro**. Esos dos cambios cierran el riesgo de seguridad más grande y hacen viable el flujo real de aprobación.

Advertencia importante: varios documentos frontend (`progress-tracker.md`) están desactualizados. Marcan como pendiente backend de consignación, join, pujas y cierre, pero el código actual ya implementa partes relevantes. Para próximas tareas, usar este backlog como mapa inicial y volver a verificar el archivo concreto antes de cambiar código.
