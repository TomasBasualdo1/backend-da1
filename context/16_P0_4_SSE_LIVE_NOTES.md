# 16 · P0.4 SSE / Live Updates

## Objetivo

Documentar la implementación de **P0.4: SSE / live updates de subastas** sobre las ramas:

- Backend: `feature/p0-4-sse-live`
- Frontend: `feature/p0-4-sse-live`

El objetivo fue que la pantalla live reciba actualizaciones de pujas/subastas en tiempo real y no dependa sólo de refresh manual, sin rehacer P0.3 ni tocar P0.5/P0.6/P1.

## Estado de partida verificado

- Backend `main` y frontend `master` estaban limpios antes de crear las ramas.
- Backend `main` se actualizó a `origin/main` por fast-forward.
- Frontend `master` se actualizó a `origin/master` por fast-forward.
- P0.3 ya estaba mergeado en backend y frontend antes de arrancar P0.4.
- El backend ya tenía un SSE básico en `/subastas/{id}/stream` y broadcast en memoria.
- El frontend `app/(tabs)/live.tsx` no consumía el stream; sólo actualizaba localmente después de pujar.

Nota de Git:

- El `fetch` inicial del backend por SSH falló con `Permission denied (publickey)`.
- Se usó una configuración temporal HTTPS con credenciales de `gh` para actualizar refs/remoto sin cambiar el `remote` persistente del repo.
- No se hizo push.
- No se usó `reset --hard`, `push --force`, `branch -D` ni se borraron ramas remotas.

## Qué se implementó

### Backend

- `GET /subastas/{id}/stream` ahora valida acceso antes de suscribir al usuario al stream.
- El stream exige:
  - token válido y no blacklisteado;
  - subasta existente;
  - subasta en estado `abierta`;
  - categoría de usuario suficiente;
  - usuario no bloqueado y sin multa activa;
  - al menos un medio de pago validado;
  - sesión activa en esa subasta, generada por `POST /subastas/{id}/join`.
- La validación del stream usa conexiones cortas a DB y luego mantiene sólo la cola SSE en memoria.
- El broadcast de puja conserva el comportamiento P0.3: si la request es replay idempotente, no se emite evento SSE duplicado.
- El evento `puja` se enriqueció para que el frontend pueda actualizar sin refetch inmediato:
  - `itemId`
  - `usuarioId`
  - `importe`
  - `mejorOfertaActual`
  - `limiteMinimo`
  - `limiteMaximo`
  - `pujaId`
  - `moneda`
  - `esGanadoraParcial`

### Frontend

- `app/(tabs)/live.tsx` abre una conexión SSE al unirse a una subasta.
- La conexión se cierra al salir de la pantalla live o al desmontar el componente.
- La pantalla actualiza en vivo:
  - oferta actual;
  - límites de puja;
  - historial visible de pujas;
  - ganador parcial por item.
- Se deduplican eventos por `pujaId` para no duplicar la puja local cuando también llega por SSE.
- El envío actual de pujas mantiene `Idempotency-Key` y el bloqueo de envío en curso.
- Se agregó reconexión simple.
- Si el stream falla, la pantalla pasa a fallback y refresca historial/detalle periódicamente.

## Archivos modificados

### Backend

- `app/api/subastas.py`
- `app/services/subasta_service.py`
- `app/repositories/subasta_repo.py`
- `tests/test_puja_idempotency.py`
- `tests/test_subasta_stream.py`

### Frontend

- `../frontend-da1/app/(tabs)/live.tsx`
- `../frontend-da1/src/services/auctionService.ts`
- `../frontend-da1/src/types/common.ts`

## Contrato SSE actual

Endpoint:

```http
GET /subastas/{id}/stream
Authorization: Bearer <access_token>
Accept: text/event-stream
```

Evento de puja:

```json
{
  "type": "puja",
  "fechaHora": "2026-06-21T00:00:00+00:00",
  "data": {
    "itemId": 9,
    "usuarioId": 12,
    "importe": 1200.0,
    "mejorOfertaActual": 1200.0,
    "limiteMinimo": 1210.0,
    "limiteMaximo": 1400.0,
    "pujaId": 77,
    "moneda": "USD",
    "esGanadoraParcial": true
  }
}
```

Evento de cierre existente:

```json
{
  "type": "cierre",
  "fechaHora": "2026-06-21T00:00:00+00:00",
  "data": {
    "message": "La subasta ha finalizado",
    "itemsCerrados": 3
  }
}
```

Keepalive:

```text
: keepalive
```

## Cómo probar manualmente

1. Levantar backend:

```bash
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

2. Loguear dos usuarios aprobados con medio validado.
3. Usuario A hace `POST /subastas/{id}/join`.
4. Usuario A abre live y queda conectado a `/subastas/{id}/stream`.
5. Usuario B hace `POST /subastas/{id}/join`.
6. Usuario B ejecuta una puja con `Idempotency-Key`.
7. Usuario A debe ver en live:
   - nuevo precio;
   - límites actualizados;
   - nueva entrada en historial.
8. Repetir la misma request de Usuario B con la misma `Idempotency-Key`.
9. Debe devolver la misma respuesta, no duplicar puja y no emitir SSE duplicado.

Prueba directa con `curl`:

```bash
curl -N \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Accept: text/event-stream" \
  http://127.0.0.1:8000/subastas/ID_SUBASTA/stream
```

## Validación ejecutada

Backend:

```bash
.venv/bin/python -m unittest tests.test_puja_idempotency -v
.venv/bin/python -m unittest tests.test_subasta_stream -v
.venv/bin/python -m unittest tests.test_flow_articulo_producto -v
.venv/bin/python -m unittest tests.test_seguridad_registro -v
.venv/bin/python -m py_compile app/api/subastas.py app/services/subasta_service.py app/repositories/subasta_repo.py tests/test_subasta_stream.py tests/test_puja_idempotency.py
git diff --check
timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

Resultado:

- `tests.test_puja_idempotency`: OK, 6 tests.
- `tests.test_subasta_stream`: OK, 3 tests.
- `tests.test_flow_articulo_producto`: OK, 6 tests.
- `tests.test_seguridad_registro`: OK, 12 tests.
- `py_compile`: OK.
- `git diff --check`: OK.
- Startup uvicorn: OK; exit `124` por timeout esperado.

Frontend:

```bash
node --version
npm --version
git diff --check
```

Resultado:

- `node --version`: no disponible en este entorno (`node: command not found`).
- `npm --version`: no disponible en este entorno (`npm: command not found`).
- `npm run lint`: no se pudo ejecutar por falta de Node/npm.
- `git diff --check`: OK.

## Fuera de alcance

- No se implementó P0.5 cierre/pagos.
- No se implementó P0.6 multas/bloqueo.
- No se implementó P1.
- No se agregó UI admin.
- No se cambió el contrato de idempotencia P0.3.
- No se agregaron migraciones.
- No se cambió el modelo de roles/admin.
- No se cambió Swagger.

## Pendientes detectados

- Probar en dispositivo/emulador con Node/npm disponible.
- Correr `npm run lint` cuando el entorno tenga Node/npm.
- Confirmar comportamiento de `XMLHttpRequest` streaming en Expo/React Native para el target real de demo. Si el runtime corta `onprogress`, el fallback de polling mantiene la pantalla viva, pero el SSE real queda `PENDIENTE DE CONFIRMAR` en dispositivo.
- Confirmar despliegue con un solo worker para que `SubastaStreamer` en memoria no pierda eventos entre procesos.
- Confirmar si el evento `item` definido por Swagger/spec debe implementarse además de `puja` y `cierre`; en esta etapa no se agregó porque el flujo actual actualiza el item desde eventos `puja`.

## Riesgos y notas técnicas

- `SubastaStreamer` sigue siendo en memoria. Funciona en un solo proceso/worker; no es un bus distribuido.
- Si Render o el servidor corre múltiples workers, cada worker tendría listeners distintos y algunos clientes podrían no recibir broadcasts.
- El stream exige sesión activa. Si el frontend llama `leave` o la sesión se finaliza por cierre, el stream siguiente será rechazado hasta volver a hacer `join`.
- La conexión SSE usa Bearer token en header, por eso se implementó con `XMLHttpRequest` en lugar de `EventSource` nativo, que no permite headers custom de forma portable.

## Qué debería pushearse / abrirse como PR

Backend:

- Rama: `feature/p0-4-sse-live`
- Base: `main`
- PR: implementación SSE validada + tests.

Frontend:

- Rama: `feature/p0-4-sse-live`
- Base: `master`
- PR: consumo live SSE + fallback/reconexión.
