# P2.1 · Mover SQL inline de routers a service/repository

## Objetivo

Mover SQL inline de routers FastAPI hacia services/repositories, sin cambiar rutas, status codes, payloads, nombres de campos, errores, autenticación, Swagger, DB, migraciones ni reglas de negocio.

## Estado inicial verificado

- Rama backend: `feature/p2-1-router-sql-cleanup`.
- HEAD inicial: `422f5402d8b58c231f4f426e410ef7036705d30d`.
- Worktree inicial: limpio.
- `grep -R "cursor.execute" -n app/api` detectó SQL inline en `auth.py`, `usuarios.py`, `notificaciones.py`, `uploads.py` y `paises.py`.
- `grep -R "db.cursor" -n app/api` detectó cursores inline en los mismos routers.
- Se leyó el contrato backend (`docs/Swagger_v5.YAML`, `app/schemas/schemas.py`) y el esquema relevante (`db/Estructura-PostgreSQL-da1-updated.sql`).
- Se leyó frontend sólo para confirmar contrato: `userService.ts`, `authService.ts` y `profile.tsx`. No hubo cambios frontend.

## Preparación Git

- No se hizo push.
- No se creó PR.
- No se cambiaron ramas durante la implementación.
- No se usó `reset --hard` ni comandos destructivos.

## Inventario de SQL inline detectado

| Router | Endpoint / función | SQL inline | Destino propuesto | Estado |
|---|---|---|---|---|
| `app/api/notificaciones.py` | `GET /usuarios/me/notificaciones` | `SELECT notificaciones` por `persona_id`, alias `fechaHora`, orden DESC | `NotificacionRepository.list_for_user` + `NotificacionService.list_notifications` | Movido |
| `app/api/notificaciones.py` | `POST /usuarios/me/notificaciones/{id}/leer` | `SELECT` ownership + `UPDATE leida=true` + commit | `NotificacionRepository.exists_for_user`, `mark_read`; service decide 404 y commit | Movido |
| `app/api/usuarios.py` | `PATCH /usuarios/me` | `SELECT nombre/documento`; `UPDATE personas`; `UPDATE personas_adicionales`; foto URL | `UsuarioService.update_profile`; repo de lectura/update | Movido |
| `app/api/usuarios.py` | `DELETE /usuarios/me/foto` | `UPDATE foto_url=NULL` + commit | `UsuarioService.delete_profile_picture` + repo | Movido |
| `app/api/usuarios.py` | `GET /usuarios/me/medios-pago` | `SELECT medios_pago` y mapeo camelCase/float/bool | `UsuarioService.list_payment_methods` + repo | Movido |
| `app/api/usuarios.py` | `POST /usuarios/me/medios-pago` | `INSERT medio`, cálculo `ultimos_digitos`, commit | `UsuarioService.add_payment_method` + repo | Movido |
| `app/api/usuarios.py` | `PATCH /usuarios/me/medios-pago/{id}` | `SELECT` ownership; `UPDATE` dinámico allowlist; no-op | `UsuarioService.update_payment_method` + repo | Movido |
| `app/api/usuarios.py` | `DELETE /usuarios/me/medios-pago/{id}` | `SELECT` ownership; `DELETE`; commit | `UsuarioService.delete_payment_method` + repo | Movido |
| `app/api/usuarios.py` | `GET /usuarios/me/metricas` | Queries COUNT/SUM/DISTINCT/MAX | `UsuarioService.get_metrics` + repo agregado | Movido |
| `app/api/auth.py` | `POST /auth/registro/paso2` | `SELECT token`; `INSERT medio_pago` opcional; commit | `AuthService.complete_registration_step2` + helpers en `UsuarioRepository` | Movido |
| `app/api/uploads.py` | `GET /uploads/fotos/{id}` | `SELECT foto` por id | Hallazgo secundario | Pendiente documentado |
| `app/api/paises.py` | `GET /paises` | `SELECT numero, nombre, capital` | Hallazgo secundario | Pendiente documentado |

## Decisiones de refactor

### Qué se movió

- `notificaciones.py` quedó delegado a `NotificacionService` y `NotificacionRepository`.
- `usuarios.py` quedó sin cursores inline para perfil, foto, medios de pago y métricas.
- `auth.py:registro_paso2` quedó delegado a `AuthService.complete_registration_step2`.
- Se reutilizó `UsuarioRepository.create_payment_method` para alta de medio de pago desde perfil y desde registro paso 2.
- El cálculo de `ultimos_digitos` quedó en service para conservar el comportamiento actual, incluido default `"4321"` cuando no hay datos.
- El SQL dinámico de update de medio de pago quedó en repository y sólo acepta columnas desde allowlist interna.

### Qué se dejó para otra etapa

- `app/api/uploads.py` conserva SQL inline porque es un hallazgo secundario fuera del alcance principal de P2.1.
- `app/api/paises.py` conserva SQL inline porque es un endpoint público simple y secundario.
- No se movió SQL histórico que ya vivía en services, porque P2.1 se limitó a deuda de routers.

### Contrato preservado

- Rutas, métodos, status codes y `response_model` se mantienen.
- Mensajes preservados:
  - `"Perfil actualizado correctamente"`.
  - `"Foto de perfil eliminada correctamente"`.
  - `"Medio de pago agregado correctamente"`.
  - `"Medio de pago actualizado"`.
  - `"No se realizaron cambios"`.
  - `"Medio de pago no encontrado"`.
  - `"Notificación marcada como leída"`.
  - `"Notificación no encontrada"`.
  - `"Token no encontrado"`.
- Alias camelCase preservados: `fechaHora`, `estadoVerificacion`, `limiteReservado`, `paisBanco`, `esCuentaReceptora`.
- Conversiones preservadas: montos a `float`, `esCuentaReceptora` a `bool`, categorías y enums vía Pydantic.
- `db.commit()` queda en service para escrituras nuevas movidas.

## Qué se implementó

### Routers

- `app/api/notificaciones.py` ahora sólo parsea dependencias y construye `Notificacion`.
- `app/api/usuarios.py` ahora delega perfil, foto, medios y métricas a `UsuarioService`.
- `app/api/auth.py:registro_paso2` ahora delega a `AuthService`.

### Services

- Nuevo `app/services/notificacion_service.py`.
- `UsuarioService` agrega métodos de perfil, foto, medios de pago y métricas.
- `AuthService` agrega `complete_registration_step2`.

### Repositories

- Nuevo `app/repositories/notificacion_repo.py`.
- `UsuarioRepository` agrega métodos para:
  - token de registro;
  - perfil editable;
  - foto de perfil;
  - CRUD de medios de pago;
  - métricas agregadas.

### Tests

- Nuevo `tests/test_notificaciones.py`.
- `tests/test_usuarios.py` amplía cobertura de perfil, foto, medios y métricas.
- `tests/test_seguridad_registro.py` cubre `registro_paso2` token 404 y medio opcional.

## Archivos modificados

- `app/api/auth.py`
- `app/api/notificaciones.py`
- `app/api/usuarios.py`
- `app/repositories/notificacion_repo.py`
- `app/repositories/usuario_repo.py`
- `app/services/auth_service.py`
- `app/services/notificacion_service.py`
- `app/services/usuario_service.py`
- `tests/test_notificaciones.py`
- `tests/test_seguridad_registro.py`
- `tests/test_usuarios.py`
- `context/14_IMPLEMENTATION_BACKLOG_FINAL.md`
- `context/23_P2_1_ROUTER_SQL_CLEANUP_NOTES.md`
- `context/README.md`

## Comandos ejecutados

```bash
git status --short --branch
git rev-parse HEAD
grep -R "cursor.execute" -n app/api
grep -R "db.cursor" -n app/api
.venv/bin/python -m py_compile app/api/auth.py app/api/usuarios.py app/api/notificaciones.py app/services/auth_service.py app/services/usuario_service.py app/repositories/usuario_repo.py app/schemas/schemas.py app/services/notificacion_service.py app/repositories/notificacion_repo.py tests/test_usuarios.py tests/test_notificaciones.py tests/test_seguridad_registro.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest tests.test_usuarios -v
.venv/bin/python -m unittest tests.test_seguridad_registro -v
.venv/bin/python -m unittest tests.test_flow_articulo_producto -v
.venv/bin/python -m unittest tests.test_email.TestConfigValidation -v
.venv/bin/python -m unittest tests.test_puja_idempotency -v
.venv/bin/python -m unittest tests.test_subasta_stream -v
.venv/bin/python -m unittest tests.test_subasta_pagos -v
.venv/bin/python -m unittest tests.test_subasta_multas -v
.venv/bin/python -m unittest tests.test_garantia_limite -v
.venv/bin/python -m unittest tests.test_subasta_listados_detalles -v
.venv/bin/python -m unittest tests.test_notificaciones -v
git diff --check
timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

## Resultados

- `py_compile`: OK.
- Suite completa: OK, 110 tests, 1 skip opt-in de email real.
- `tests.test_usuarios`: OK, 14 tests.
- `tests.test_seguridad_registro`: OK, 14 tests.
- `tests.test_flow_articulo_producto`: OK, 6 tests.
- `tests.test_email.TestConfigValidation`: OK, 6 tests.
- `tests.test_puja_idempotency`: OK, 6 tests.
- `tests.test_subasta_stream`: OK, 3 tests.
- `tests.test_subasta_pagos`: OK, 12 tests.
- `tests.test_subasta_multas`: OK, 13 tests.
- `tests.test_garantia_limite`: OK, 15 tests.
- `tests.test_subasta_listados_detalles`: OK, 10 tests.
- `tests.test_notificaciones`: OK, 5 tests.
- `grep -R "cursor.execute" -n app/api` después del refactor sólo lista `uploads.py` y `paises.py`.
- `grep -R "db.cursor" -n app/api` después del refactor sólo lista `uploads.py` y `paises.py`.
- `git diff --check`: OK.
- Uvicorn: startup OK en `http://0.0.0.0:8001`; salida `124` esperada por `timeout 8s`.

## Riesgos / pendientes

- Pendiente documentado: mover SQL inline secundario de `uploads.py` y `paises.py` si el equipo decide ampliar P2.1 o crear una etapa chica posterior.
- `AuthService`, `AdminService` y otros services todavía contienen SQL histórico; no se tocó porque la deuda pedida era SQL inline de routers.
- No se modificó frontend porque el contrato observable no cambió.
- No se modificó Swagger, schemas generados ni DB.
