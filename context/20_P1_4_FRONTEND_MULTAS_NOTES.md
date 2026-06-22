# P1.4 · Pago de multas en frontend

## Objetivo

Permitir que el usuario pague multas pendientes desde la pestaña `Pagos y Multas` del perfil, usando un medio de pago propio, validado y compatible.

## Estado inicial verificado

- Backend P0.6 ya exponia `GET /usuarios/me/multas` y `POST /usuarios/me/multas/pagar`.
- `UsuarioService.pagar_multa` valida multa propia, estado `pendiente`, medio propio, `estado_verificacion='validado'` y limite reservado suficiente cuando `limite_reservado > 0`.
- Frontend ya tenia `userService.getMultas()` y `userService.pagarMulta(data)`.
- `profile.tsx` cargaba `medios` y `multas`, pero solo mostraba las multas como listado sin CTA de pago.
- `app/pagos/[subastaId].tsx` ya tenia un patron util de evaluacion de medios, selector y motivos de incompatibilidad.

## Dependencias verificadas

### P0.6

Confirmado en codigo y documentacion local:

- `app/api/usuarios.py` delega `POST /usuarios/me/multas/pagar` a `UsuarioService.pagar_multa`.
- `app/services/usuario_service.py` procesa vencimientos lazy antes de listar/pagar multas.
- `app/repositories/usuario_repo.py` devuelve multas y medios propios con los campos necesarios.
- `tests/test_subasta_multas.py` cubre pago con medio ajeno, medio no validado, limpieza de `multa_activa` y bloqueo de login.

### P1.2 / P1.3 en paralelo

La implementacion se limito a:

- helpers/estado local de pago de multas en `profile.tsx`;
- render de multas dentro de `tab === "pagos"`;
- estilos locales de esa seccion;
- refresh de multas, medios y perfil despues del pago.

No se tocaron pantallas admin, navegacion admin, consignaciones, tasacion ni flujo de articulos.

## Decisiones de implementación

- No se agrego componente nuevo para evitar ampliar superficie de conflicto; el cambio quedo local a la pestaña `pagos`.
- No se filtro por moneda de multa porque el backend no modela moneda en `multas`.
- Se evalua compatibilidad por multa:
  - medio sin `id`: incompatible;
  - `estadoVerificacion !== "validado"`: incompatible;
  - `limiteReservado > 0 && limiteReservado < importe`: incompatible.
- Se preselecciona el primer medio compatible por multa pendiente.
- Se guarda solo el `id` del medio seleccionado por multa; no se guardan datos sensibles nuevos.
- El request se confirma con `Alert.alert` antes de llamar al backend.
- Los errores HTTP se mapearon a mensajes especificos para `400`, `403`, `404` y `409`.

## Qué se implementó

### Frontend

- En `app/(tabs)/profile.tsx`:
  - CTA `Pagar` solo para multas `pendiente` con `id` valido;
  - multas `pagada` sin CTA;
  - selector de medio de pago por multa;
  - medios no validados, sin id o con limite insuficiente marcados como incompatibles;
  - mensaje claro cuando no hay medios registrados o no hay medios validados;
  - confirmacion previa al pago;
  - loading y bloqueo de accion durante el request;
  - llamada a `userService.pagarMulta({ multaId, medioPagoId })`;
  - refresh posterior de `getMultas()`, `getMediosPago()` y `refreshUser()`;
  - aviso visible de que `multaActiva` impide participar en nuevas subastas.
- Bonus fix de alineacion con consigna:
  - `abierta` dejo de usarse como sinonimo visual de `EN VIVO`;
  - se agrego `src/utils/auctionSchedule.ts` para evaluar fecha/hora local;
  - home, listado, detalle y sala live muestran `EN VIVO` solo si la subasta esta `abierta`, es el dia actual y ya paso su hora de inicio;
  - subastas futuras abiertas se muestran como `PROGRAMADA`/proximas;
  - el detalle ya no ofrece pagar deuda para subastas programadas, solo para subastas cerradas.

### Backend, si aplica

No hubo cambios funcionales de backend. Solo se agrego esta nota y se actualizo el estado P1.4 en el backlog.

## Archivos modificados

- `frontend-da1/app/(tabs)/profile.tsx`
- `frontend-da1/app/(tabs)/index.tsx`
- `frontend-da1/app/(tabs)/subastas.tsx`
- `frontend-da1/app/(tabs)/live.tsx`
- `frontend-da1/app/subasta/[id]/index.tsx`
- `frontend-da1/src/utils/auctionSchedule.ts`
- `backend-da1/context/20_P1_4_FRONTEND_MULTAS_NOTES.md`
- `backend-da1/context/14_IMPLEMENTATION_BACKLOG_FINAL.md`

## Validación ejecutada

- `which node`: no disponible en este entorno.
- `which npm`: no disponible en este entorno.
- `which npx`: no disponible en este entorno.
- `npm run lint`: no ejecutado porque `npm` no esta disponible.
- `npx tsc --noEmit`: no ejecutado porque `npx` no esta disponible.
- `git diff --check` en `frontend-da1`: OK.
- `git diff --check` en `backend-da1`: OK.
- `.venv/bin/python -m unittest tests.test_subasta_multas -v`: OK, 13 tests.
- `.venv/bin/python -m unittest tests.test_seguridad_registro -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_flow_articulo_producto -v`: OK, 6 tests.
- `.venv/bin/python -m unittest tests.test_email.TestConfigValidation -v`: OK, 6 tests.
- `.venv/bin/python -m py_compile app/api/usuarios.py app/services/usuario_service.py app/repositories/usuario_repo.py app/schemas/schemas.py`: OK.

## Validación manual recomendada

1. Perfil con multa pendiente muestra CTA `Pagar`.
2. Multa pagada no muestra CTA.
3. Sin medios registrados muestra mensaje claro.
4. Sin medios validados muestra mensaje claro.
5. Medio no validado aparece incompatible.
6. Medio con `limiteReservado > 0` menor al importe aparece incompatible.
7. Medio validado y compatible puede seleccionarse.
8. Confirmar pago llama `POST /usuarios/me/multas/pagar` con `{ multaId, medioPagoId }`.
9. Exito refresca multas y perfil, limpiando `multaActiva` si backend ya no tiene multas pendientes.
10. Errores `400`, `403`, `404`, `409` muestran mensajes entendibles.
11. Alta y eliminacion de medios de pago siguen funcionando.
12. No se altera la zona de consignaciones/P1.3 ni admin/P1.2.

## Riesgos / pendientes

- Validacion automatica frontend queda pendiente hasta tener `node`, `npm` y `npx` disponibles.
- La UI solo puede pagar multas que el backend ya devuelve; no cambia reglas de generacion/vencimiento de P0.6.
- La moneda de multa no esta modelada en backend; se muestra el importe sin filtrar medios por moneda.
