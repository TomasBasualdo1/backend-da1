# 17 · P0.5 Cierre / Deuda / Pago de Subasta

Fecha: 2026-06-21

## Objetivo

Completar el flujo post-subasta sin mezclar P0.6:

- cierre manual protegido por admin;
- generacion de deuda por ganador;
- confirmacion de pago con el medio especifico del usuario;
- pantalla minima para consultar y pagar una deuda de subasta puntual.

## Backend implementado

- `POST /subastas/{id}/cerrar` conserva `require_admin(user)`.
- El guard admin actual se tomo de `app/dependencies.py`: `usuarioId == 12`.
- El cierre sigue:
  - marcando items como subastados;
  - registrando ventas para items con puja ganadora;
  - notificando ganadores;
  - notificando al duenio cuando la empresa adquiere un item sin pujas;
  - generando un pago por cliente ganador;
  - finalizando sesiones y manteniendo el broadcast SSE del router.
- `SubastaRepository.generar_pago` primero busca un pago existente para la misma subasta y cliente, para evitar duplicados en reintentos parciales.
- `SubastaService.confirmar_pago` ahora valida:
  - que el pago exista y este pendiente;
  - `medioPagoId` propio del usuario autenticado;
  - `estado_verificacion == 'validado'`;
  - moneda del medio igual a moneda del pago;
  - fondos/limite suficientes cuando `limite_reservado > 0`;
  - direccion obligatoria para `envio`;
  - consentimiento explicito de perdida de seguro para `retiro`.
- La confirmacion persiste `medio_pago_id`, `modo_entrega`, `direccion_envio`, `costo_envio`, `total_final`, `acepta_perder_seguro` y marca el pago como `pagado`.
- El service hace un solo `db.commit()` tras confirmar pago y crear la notificacion; ante error hace `rollback()`.

## Frontend implementado

- Nueva pantalla `app/pagos/[subastaId].tsx`.
- En subastas cerradas, `app/subasta/[id]/index.tsx` muestra CTA hacia el pago.
- La pantalla usa:
  - `auctionService.getPago(subastaId)`;
  - `auctionService.confirmarPago(subastaId, payload)`;
  - `userService.getMediosPago()`.
- La UI muestra:
  - `totalPujado`, `comision`, `costoEnvio`, `totalFinal`, `moneda`, `fechaLimitePago`;
  - selector de medios con incompatibilidades visibles;
  - `envio` o `retiro`;
  - direccion obligatoria para `envio`;
  - confirmacion visible de perdida de seguro para `retiro`.
- No se agrego endpoint de listado global de pagos pendientes porque el backend actual solo expone `GET /subastas/{id}/pagos`.

## Decisiones

- Moneda: se mantiene `USD` al generar pagos porque `subastas` no tiene columna `moneda` en `db/Estructura-PostgreSQL-da1-updated.sql`.
- Costo de envio: se mantiene el costo fijo actual de `500.0` cuando `modo_entrega == 'envio'`.
- Retiro: el backend rechaza si `aceptaPerderSeguro` no viene en `true`; si viene en `true`, persiste `acepta_perder_seguro = true` y limpia `direccion_envio`.
- Codigos HTTP:
  - `400` para reglas de negocio;
  - `403` para medio ajeno/no autorizado o no validado;
  - `404` cuando no hay pago para esa subasta;
  - `409` cuando el pago no esta pendiente.

## Fuera de alcance

- No se implemento generacion automatica de multa del 10%.
- No se marcaron pagos vencidos.
- No se agrego scheduler/job/lazy trigger de vencimientos.
- No se implemento pago de multas desde perfil.
- No se tocaron categoria automatica, deploy, env ni roles/admin.
- No se agregaron migraciones.

## PENDIENTE DE CONFIRMAR

- Confirmar si la moneda real de cada subasta debe persistirse con una migracion nueva o si `USD` queda aceptado para la demo.
- Confirmar la formula real de `costo_envio`; hoy se conserva `500.0` fijo.
- Confirmar como debe modelarse contablemente "empresa compra al precio base" cuando no hay pujas; hoy se marca el item y se notifica al duenio, pero no se crea una entidad/registro adicional para la empresa.
- Confirmar si el limite reservado debe descontarse/reservarse al pagar o solo validarse contra el total de compra. En P0.5 solo se valida suficiencia.
- Confirmar si corresponde un endpoint de listado de pagos pendientes del usuario para alimentar una seccion global en perfil.

## Validacion

- `.venv/bin/python -m unittest tests.test_subasta_pagos -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_seguridad_registro tests.test_puja_idempotency tests.test_subasta_stream -v`: OK, 21 tests.
- `.venv/bin/python -m py_compile app/api/subastas.py app/services/subasta_service.py app/repositories/subasta_repo.py tests/test_subasta_pagos.py`: OK.
- `git diff --check` en backend y frontend: OK.
- `node --version` en frontend: no disponible en este entorno (`node: command not found`), por lo que no se ejecuto lint/TypeScript.
