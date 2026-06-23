# P1.1 · Alineación de listados/detalles de subastas

## Objetivo

Alinear listados y detalles de subastas con Swagger y el frontend actual sin reimplementar P0.1-P0.7 ni ampliar alcance administrativo.

## Estado inicial verificado

- `GET /subastas/publicas` no filtraba explicitamente `s.estado = 'abierta'`.
- `GET /subastas` reutilizaba el listado publico.
- El detalle publico podia devolver subastas cerradas y no tenia filtro de estado.
- El detalle autenticado no validaba la categoria del usuario antes de exponer precios.
- `subastado` podia salir como `False`, aunque Swagger y TypeScript esperan `"si" | "no"`.
- `subastas` no tiene columna `moneda`; pagos si tiene `moneda`.

## Decisiones de contrato

### Subastas públicas

Devuelven solo subastas `abierta`, con shape `SubastaListadoPublico`, sin precios de catalogo.

### Subastas autenticadas

Devuelven el listado amplio de subastas `abierta`. La elegibilidad fina de participacion sigue en `join`, `stream` y `pujar`; el frontend puede mostrar candados por categoria.

### Detalle público

Devuelve solo subastas `abierta`. Una subasta cerrada o inexistente responde como no encontrada. No expone `precioBase`, `limiteMinimo` ni `limiteMaximo`.

### Detalle autenticado

Valida categoria con el orden `comun < especial < plata < oro < platino`. Si la categoria del usuario no alcanza, responde `403`. Si alcanza, expone `precioBase`, `limiteMinimo` y `limiteMaximo`. No exige join ni medio validado para ver el detalle.

### Campo subastado

Backend y frontend usan el contrato canonico `"si" | "no"`. El frontend acepta temporalmente `false`, `true`, `"false"` y `"true"` para tolerar respuestas viejas.

### Moneda

Se mantiene `"USD"` como default explicito en listados/detalles/pujas/pagos actuales porque el esquema vigente no tiene `subastas.moneda`.

PENDIENTE DE CONFIRMAR / P2.3: definir si la moneda real de cada subasta requiere migracion o si `USD` queda aceptado para la demo.

## Qué se implementó

### Backend

- `SubastaRepository.get_publicas` y `get_todas` filtran `s.estado = 'abierta'`.
- `SubastaRepository.get_publica_detalle` filtra detalle publico por subasta abierta.
- `SubastaService.get_detalle` recibe `usuario_id` y `categoria_usuario` desde el router y valida categoria antes de devolver detalle autenticado.
- `SubastaRepository` normaliza `subastado` a `"si" | "no"` y mantiene `moneda = "USD"`.
- `schemas.py` corrige `Subastado` para `si/no`.
- Swagger documenta `403` en detalle autenticado y la limitacion actual de moneda.

### Frontend

- `auctionService` normaliza listados y detalles: `subastado`, `catalogo`, `fotos`, `moneda` y campos numericos.
- `subasta/[id]` muestra un mensaje claro cuando el detalle autenticado responde `403`.

## Archivos modificados

- `app/api/subastas.py`
- `app/services/subasta_service.py`
- `app/repositories/subasta_repo.py`
- `app/schemas/schemas.py`
- `docs/Swagger_v5.YAML`
- `tests/test_subasta_listados_detalles.py`
- `context/14_IMPLEMENTATION_BACKLOG_FINAL.md`
- `context/20_P1_1_AUCTION_LISTINGS_DETAILS_NOTES.md`
- `../frontend-da1/src/services/auctionService.ts`
- `../frontend-da1/app/subasta/[id]/index.tsx`
- `../frontend-da1/context/progress-tracker.md`

## Tests ejecutados

- `.venv/bin/python -m unittest tests.test_subasta_listados_detalles -v`: OK, 10 tests.
- `.venv/bin/python -m unittest tests.test_puja_idempotency -v`: OK, 6 tests.
- `.venv/bin/python -m unittest tests.test_subasta_stream -v`: OK, 3 tests.
- `.venv/bin/python -m unittest tests.test_subasta_pagos -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_subasta_multas -v`: OK, 13 tests.
- `.venv/bin/python -m unittest tests.test_seguridad_registro -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_flow_articulo_producto -v`: OK, 6 tests.
- `.venv/bin/python -m unittest tests.test_email.TestConfigValidation -v`: OK, 6 tests.
- `.venv/bin/python -m py_compile app/api/subastas.py app/services/subasta_service.py app/repositories/subasta_repo.py app/schemas/schemas.py`: OK.
- Backend `git diff --check`: OK.
- Frontend `git diff --check`: OK.
- Frontend `npm run lint`: NO EJECUTADO, `node` y `npm` no estan disponibles en este entorno.

## Validación manual

- `timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001`: OK. El servidor completo startup y el proceso fue cortado por `timeout` con codigo 124 esperado.

## Riesgos / pendientes

- PENDIENTE DE CONFIRMAR / P2.3: moneda real por subasta; el esquema no tiene `subastas.moneda`.
- El listado autenticado muestra abiertas de todas las categorias; el bloqueo visual de categoria queda del lado frontend y la validacion dura se mantiene en detalle/join/stream/puja.
- El detalle autenticado conserva subastas cerradas si se accede por ruta historica para no romper el CTA de pago existente.
