# P1.5 · Limite por garantia / cheque certificado

## Objetivo

Implementar la regla del TPO: si el usuario dejo un monto como garantia de pago, sus compras no pueden superar ese monto, pero mientras alcance puede participar en tantas subastas como quiera.

## Estado inicial verificado

- `medios_pago.limite_reservado` existe en `db/Estructura-PostgreSQL-da1-updated.sql`.
- `MedioPago.limiteReservado` existe en `app/schemas/schemas.py` y en `frontend-da1/src/types/payment.ts`.
- `app/api/usuarios.py` crea/edita medios con `limiteReservado`.
- `SubastaService.procesar_puja` validaba join, multas/bloqueo, idempotencia, lock `SELECT ... FOR UPDATE`, limites 1%/20% y premium, pero no exposicion por garantia.
- `SubastaService.confirmar_pago` y `UsuarioService.pagar_multa` ya validaban limite del medio elegido para pagos concretos.

## Preparacion Git

- Backend verificado en `feature/p1-5-garantia-limite`.
- Frontend verificado en `feature/p1-5-garantia-limite`.
- No se hizo push ni PR.
- No se uso `reset --hard` ni borrado forzado de ramas.

## Dependencias verificadas

### P0.3 / Idempotencia

`app/repositories/puja_repo.py` y `db/migration_p0_3_puja_idempotency.sql` existen. La validacion de garantia se ejecuta solo para requests no completadas; un replay `completed` devuelve la respuesta cacheada sin recalcular exposicion ni duplicar SSE.

### P0.4 / SSE

El router emite SSE solo despues de que `procesar_puja` devuelve OK. Si P1.5 rechaza por garantia, no hay `broadcast`.

### P0.5 / Cierre y pagos

`confirmar_pago` mantiene la validacion de medio propio, validado, moneda compatible y limite suficiente para el pago especifico. P1.5 no reemplaza esa validacion.

### P0.6 / Multas y bloqueo

`procesar_puja` sigue procesando vencimientos y rechazando usuarios bloqueados o con multa pendiente antes de competir por garantia.

### P1.4 / Pago de multas frontend

El perfil ya evalua medios para multas. P1.5 no modifica ese flujo.

## Decisiones de negocio

### Cuando se valida la garantia

No se reserva al join. La garantia se valida al pujar, despues de validar item y limites de monto y antes de registrar la puja.

### Que compone la exposicion del usuario

- Pagos pendientes (`pagos.estado = 'pendiente'`) usando `total_final`.
- Pujas ganadoras parciales actuales del usuario en subastas abiertas.
- Solo cuenta la mejor puja vigente por item.
- La puja candidata se suma a la exposicion.
- Si el usuario ya lidera el mismo item, la candidata reemplaza el importe anterior.
- No se suman pujas superadas, pagos `pagado`, pagos `vencido` ni multas pendientes.

### Como se tratan multiples medios

Se suman los medios propios validados con limite positivo y moneda compatible. La consulta bloquea esas filas con `FOR UPDATE` para serializar pujas simultaneas del mismo usuario contra la misma garantia.

### Que pasa con medios sin limite

`limite_reservado = 0` no aporta fondos y no se interpreta como ilimitado. Si el usuario no dejo ningun medio validado con limite positivo, P1.5 no bloquea por esta regla, siempre que ya cumpla el join con un medio validado. `PENDIENTE DE CONFIRMAR`: si negocio quiere exigir garantia positiva para toda puja, habria que endurecer esta decision.

### Moneda

Como `subastas` no persiste moneda y el flujo actual usa `USD`, P1.5 filtra garantia y pagos por `USD`.

## Que implementa P1.5

### Backend

- Agrega consultas en `SubastaRepository` para:
  - garantia validada y bloqueada con `FOR UPDATE`;
  - pagos pendientes que consumen exposicion;
  - pujas ganadoras parciales activas por mejor puja vigente de cada item.
- Agrega validacion en `SubastaService.procesar_puja` antes de `registrar_puja`.
- Rechaza con `400` y `detail.codigo = GARANTIA_INSUFICIENTE`.
- Mantiene commits en service y SQL en repository.

### Frontend

- `live.tsx` reconoce `GARANTIA_INSUFICIENTE` y muestra garantia disponible, importe requerido y exposicion actual.
- No se agrega endpoint de garantia disponible; la UI no anticipa exposicion acumulada y depende del rechazo backend.

## Archivos modificados

- `app/repositories/subasta_repo.py`
- `app/services/subasta_service.py`
- `app/schemas/schemas.py`
- `docs/Swagger_v4.YAML`
- `tests/test_garantia_limite.py`
- `context/14_IMPLEMENTATION_BACKLOG_FINAL.md`
- `context/21_P1_5_GARANTIA_LIMITE_NOTES.md`
- `frontend-da1/src/types/auction.ts`
- `frontend-da1/app/(tabs)/live.tsx`
- `frontend-da1/context/11_INTEGRATION.md`

## Tests

- `tests/test_garantia_limite.py` cubre garantia suficiente/insuficiente, pagos pendientes, pujas ganadoras parciales, pujas superadas, candidata nueva, reemplazo del mismo item, multiples medios, medio no validado, limite cero, pago P0.5, rollback/idempotencia, replay idempotente y bloqueo/multa antes de garantia.

## Validacion ejecutada

- `.venv/bin/python -m unittest tests.test_garantia_limite -v`
- `.venv/bin/python -m unittest tests.test_puja_idempotency -v`
- `.venv/bin/python -m unittest tests.test_subasta_stream -v`
- `.venv/bin/python -m unittest tests.test_subasta_pagos -v`
- `.venv/bin/python -m unittest tests.test_subasta_multas -v`
- `.venv/bin/python -m unittest tests.test_subasta_listados_detalles -v`
- `.venv/bin/python -m unittest tests.test_seguridad_registro -v`
- `.venv/bin/python -m unittest tests.test_flow_articulo_producto -v`
- `.venv/bin/python -m unittest tests.test_email.TestConfigValidation -v`
- `.venv/bin/python -m py_compile app/api/subastas.py app/services/subasta_service.py app/repositories/subasta_repo.py app/repositories/puja_repo.py app/api/usuarios.py app/repositories/usuario_repo.py app/schemas/schemas.py`
- `git diff --check` en backend.
- `timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001` arranco correctamente y fue detenido por `timeout`.
- `git diff --check` en frontend.
- `npm run lint` no se pudo ejecutar porque `npm` no esta instalado en este entorno.

## Riesgos / pendientes

- `PENDIENTE DE CONFIRMAR`: si todos los usuarios deben tener garantia positiva para pujar o solo aplica a quienes dejaron garantia limitada.
- `PENDIENTE DE CONFIRMAR`: moneda real por subasta. P1.5 conserva `USD` porque el esquema actual no tiene columna de moneda en `subastas`.
- No se implemento ledger, reserva persistente ni endpoint de exposicion disponible.
