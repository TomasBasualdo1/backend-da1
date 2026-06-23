# 19 · P0.6 Multas / Vencimientos / Bloqueo

Fecha: 2026-06-21

## Objetivo

Completar el flujo backend de incumplimiento post-subasta:

- detectar pagos de subasta vencidos;
- marcar esos pagos como `vencido`;
- generar una multa idempotente del 10% sobre `pagos.total_pujado`;
- mantener `clientes_adicionales.multa_activa = true` mientras haya multa pendiente;
- impedir participacion cuando el usuario tenga multa activa o bloqueo fuerte;
- permitir pagar multas con medio propio validado;
- bloquear usuarios cuando vence una multa pendiente.

## Backend implementado

- Nuevo endpoint manual protegido:
  - `POST /admin/pagos/procesar-vencimientos`
  - requiere `require_admin(user)`, admin actual `usuarioId == 12`.
  - devuelve resumen:
    - `pagosVencidosProcesados`
    - `multasCreadas`
    - `usuariosMarcadosMultaActiva`
    - `usuariosBloqueados`
    - `multasVencidasBloqueantes`
- `SubastaService.procesar_vencimientos(db, usuario_id=None)`:
  - consulta pagos `estado='pendiente'` con `fecha_limite_pago < NOW()`;
  - marca el pago como `vencido`;
  - genera multa del 10% de `total_pujado`;
  - crea notificaciones `pago` y `sistema`;
  - procesa multas pendientes vencidas y aplica `bloqueado=true`.
- Validacion lazy:
  - antes de `join_subasta`;
  - antes de `validar_acceso_stream`;
  - antes de `procesar_puja`;
  - al consultar `GET /subastas/{id}/pagos`;
  - al listar/pagar multas desde `UsuarioService`.
- Pago de multas:
  - movido de SQL inline en router a `UsuarioService` + `UsuarioRepository`;
  - valida que la multa sea propia y este `pendiente`;
  - valida que `medioPagoId` sea propio;
  - valida `estado_verificacion='validado'`;
  - si `limite_reservado > 0`, exige que cubra el importe de la multa;
  - marca `multas.estado='pagada'` y guarda `medio_pago_id`;
  - si no quedan multas pendientes, limpia `multa_activa=false`;
  - crea notificacion `pago`.

## Reglas exactas

- Pago vencido: `pagos.estado = 'vencido'` cuando `estado='pendiente'` y `fecha_limite_pago < NOW()`.
- Multa: `10%` de `pagos.total_pujado`.
- Idempotencia de multa sin migracion: `motivo = "Incumplimiento de pago #{pago_id} subasta #{subasta_id}"`.
- Duplicados: antes de insertar se busca multa del mismo `cliente_id` con ese `motivo`; si existe, no se duplica.
- Multa activa: si existe multa pendiente generada o encontrada para ese incumplimiento, queda `clientes_adicionales.multa_activa=true`.
- Participacion: `join`, `stream` y nueva puja rechazan con `403` cuando `SubastaRepository.puede_participar` detecta `multa_activa` o `bloqueado`.
- Bloqueo fuerte: si una multa pendiente vence (`multas.fecha_limite < NOW()`), el procesamiento setea `clientes_adicionales.bloqueado=true`. Login ya rechaza `bloqueado=true` en `AuthService.login`.

## Archivos tocados

Backend:

- `app/api/admin.py`
- `app/api/usuarios.py`
- `app/services/subasta_service.py`
- `app/services/usuario_service.py`
- `app/repositories/subasta_repo.py`
- `app/repositories/usuario_repo.py`
- `app/schemas/schemas.py` no requirio cambios.
- `docs/Swagger_v5.YAML`
- `tests/test_puja_idempotency.py`
- `tests/test_subasta_multas.py`

Frontend:

- No se modifico en esta corrida. El intento de editar `../frontend-da1/app/(tabs)/profile.tsx` fue bloqueado por permisos/revision del entorno al estar fuera del root writable actual.

## Validacion

- `.venv/bin/python -m unittest tests.test_subasta_multas -v`: OK, 13 tests.
- `.venv/bin/python -m unittest tests.test_subasta_pagos -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_puja_idempotency tests.test_subasta_stream tests.test_seguridad_registro -v`: OK, 21 tests.
- `.venv/bin/python -m py_compile app/api/subastas.py app/api/usuarios.py app/api/admin.py app/services/subasta_service.py app/services/usuario_service.py app/repositories/subasta_repo.py app/repositories/usuario_repo.py tests/test_subasta_multas.py`: OK.

## Limitaciones

- Frontend pendiente por bloqueo de escritura fuera de `/home/rama/Documents/DA1/backend-da1`.
- No se implemento scheduler/cron externo.
- El procesamiento automatico depende del endpoint admin manual y de validaciones lazy.
- No se agrego migracion ni columna `multas.pago_id`.
- La moneda de multa no esta modelada en `multas`; se valida medio propio/validado y limite reservado, pero no moneda.

## PENDIENTE DE CONFIRMAR

- PENDIENTE DE CONFIRMAR si el equipo acepta una migracion robusta con `multas.pago_id` + unique parcial.
- PENDIENTE DE CONFIRMAR si Render tendra scheduler/worker confiable; por ahora se evita cron externo.
- PENDIENTE DE CONFIRMAR si la multa debe calcularse sobre `total_pujado` o sobre otro monto final. Se uso `total_pujado` por TPO/contexto actual.
- PENDIENTE DE CONFIRMAR si el bloqueo fuerte debe dispararse por multa vencida, por pago original vencido una segunda vez, o por otro hito administrativo. Se eligio multa pendiente vencida porque el esquema actual solo ofrece `multas.fecha_limite`.
- PENDIENTE DE CONFIRMAR implementacion frontend de CTA y selector de medio validado cuando haya permisos de escritura en `frontend-da1`.
