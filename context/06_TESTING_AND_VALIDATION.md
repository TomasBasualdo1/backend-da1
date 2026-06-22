# 06 · Testing & Validación

## Estado de testing

- Framework: **`unittest`** de la stdlib. No convertir la suite a pytest para P1.6.
- Comando principal backend: **`python -m unittest discover -s tests -v`**.
- La suite backend corre con DB mockeada y llamadas directas a endpoints async/services/repositories. **No requiere Postgres real, internet, SendGrid/Resend real ni servicios externos.**
- El envío real de email quedó como integración opt-in: sólo corre con `RUN_REAL_EMAIL_TESTS=1`.
- No hay linter/formatter Python configurado en el repo.
- Frontend: no hay Jest, Vitest ni React Native Testing Library configurados. `package.json` sólo tiene script de validación `lint`; en este entorno `node`/`npm` no están disponibles.

## Suite backend actual

| Archivo | Cubre |
|---------|-------|
| `tests/test_email.py` | Configuración de email, providers mockeados (`resend`, `sendgrid`, `smtp`) y envío real opt-in. |
| `tests/test_flow_articulo_producto.py` | Consignación: publicar artículo, evaluación admin, aceptar/rechazar tasación y conversión a seguro/producto/fotos. |
| `tests/test_garantia_limite.py` | P1.5 garantía/límite, exposición por pagos/pujas, replay idempotente y queries de garantía. |
| `tests/test_puja_idempotency.py` | `Idempotency-Key`, replays, conflictos, request nueva y SSE no duplicado. |
| `tests/test_seguridad_registro.py` | Registro pendiente, login bloqueado por pendiente, guards admin y aprobación/rechazo. |
| `tests/test_subasta_listados_detalles.py` | Listados/detalles P1.1, filtros `abierta`, precio visible según contrato y moneda `USD` documentada. |
| `tests/test_subasta_multas.py` | P0.6 vencimientos, multas idempotentes, bloqueo, pago de multas y login bloqueado. |
| `tests/test_subasta_pagos.py` | P0.5 cierre, generación de pagos, medio propio/validado, moneda, límite, envío/retiro. |
| `tests/test_subasta_stream.py` | P0.4 acceso SSE con sesión activa y validación antes de suscripción. |
| `tests/test_usuarios.py` | Perfil `GET /usuarios/me`, 404 y `DELETE /usuarios/me/foto` con SQL/commit verificados. |

## Cómo correr los tests backend

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m unittest tests.test_usuarios -v
python -m unittest tests.test_email -v
```

Para ejecutar manualmente el test de integración real de email:

```bash
RUN_REAL_EMAIL_TESTS=1 python -m unittest tests.test_email.TestEmailService.test_integration_real_send -v
```

> Este comando usa el provider y las credenciales reales del entorno. No debe ejecutarse en la suite local por defecto.

## FastAPI TestClient

En este virtualenv se reprodujo un cuelgue de `fastapi.testclient.TestClient` incluso con una app FastAPI mínima (`fastapi 0.136.1`, `starlette 1.0.0`, `anyio 4.13.0`, Python 3.13.5). Por eso `tests/test_usuarios.py` prueba los endpoints async directamente con DB mockeada y asserts de SQL/commit, en línea con el patrón usado por el resto de la suite.

Si más adelante se reintroduce `TestClient`, usar siempre:

- `app.dependency_overrides[...]` sólo dentro del test que lo necesita.
- `try/finally` o `tearDown` con `app.dependency_overrides.clear()`.
- Timeout corto al validar localmente para detectar cuelgues de tooling.

## Validación frontend

Scripts reales en `frontend-da1/package.json`:

```bash
npm run lint
```

No hay script `test`, `typecheck`, Jest, Vitest ni RTL configurados. `npx tsc --noEmit` puede servir como validación manual si Node/npm están disponibles, pero no es script del repo.

En este entorno:

- `node` no está disponible.
- `npm` no está disponible.
- Por lo tanto, `npm run lint` queda pendiente para un entorno con Node.
- No agregar infraestructura de tests frontend en P1.6 salvo decisión explícita del equipo.

## Checklist antes de commitear

- [ ] `python -m unittest discover -s tests -v` pasa sin red real.
- [ ] `python -m py_compile` sobre archivos Python tocados pasa.
- [ ] `git diff --check` pasa.
- [ ] Si tocaste frontend y existe Node/npm, corré `npm run lint`.
- [ ] No se ejecutó email real salvo `RUN_REAL_EMAIL_TESTS=1`.
- [ ] No se commitearon secretos ni cambios de `.env`.
