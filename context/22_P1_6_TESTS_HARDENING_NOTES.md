# P1.6 · Fortalecer tests automatizados

Fecha: 2026-06-22

## Objetivo

Estabilizar la suite backend para que `python -m unittest discover -s tests -v` termine limpia y rápido sin Postgres real, internet, SendGrid/Resend real ni servicios externos.

## Estado inicial verificado

- La suite completa no terminaba: `test_email.TestEmailService.test_integration_real_send` intentaba DNS/red real y después `tests.test_usuarios` quedaba colgado.
- `fastapi.testclient.TestClient` cuelga en este virtualenv incluso con una app FastAPI mínima.
- Los demás tests de P0.3/P0.4/P0.5/P0.6/P1.1/P1.5 pasaban de forma aislada con mocks.
- Frontend no tiene infraestructura de tests. `package.json` expone `lint`, pero `node` y `npm` no están disponibles en este entorno.

## Qué se implementó

### Backend

- `tests/test_email.py`:
  - el test de envío real quedó detrás de `RUN_REAL_EMAIL_TESTS=1`;
  - los tests mockeados de Resend, SendGrid y SMTP siguen corriendo por defecto.
- `tests/test_usuarios.py`:
  - se eliminó la dependencia del `TestClient` colgado;
  - se conservó la cobertura de endpoint async real para `GET /usuarios/me`, `404` y `DELETE /usuarios/me/foto`;
  - se agregaron asserts de SQL/params y `db.commit()`.
- `context/06_TESTING_AND_VALIDATION.md`:
  - actualizado con los 10 archivos de tests reales, comandos actuales, email opt-in y validación frontend real.

### Frontend

- No se agregó Jest/Vitest/RTL porque no existe base de tooling y P1.6 no lo justifica.
- Se validó `package.json`: el único script de validación existente es `npm run lint`.
- La ejecución queda pendiente en este entorno porque `node`/`npm` no están instalados.

## Decisiones

- Se mantiene `unittest` de stdlib.
- No se agregan skips para ocultar bugs funcionales. El único skip por defecto es el envío real de email, que es una integración externa explícita.
- El cuelgue de `TestClient` se trata como limitación de tooling local, no como excusa para borrar cobertura: los endpoints se prueban llamando las funciones async con DB mockeada.
- No se reimplementan features previas ni se agregan migraciones.

## Validación ejecutada

- `.venv/bin/python -m unittest discover -s tests -v`: OK, 92 tests, 1 skip opt-in de email real.
- `.venv/bin/python -m unittest tests.test_usuarios -v`: OK, 3 tests.
- `.venv/bin/python -m unittest tests.test_email -v`: OK, 12 tests, 1 skip opt-in.
- `.venv/bin/python -m unittest tests.test_email.TestConfigValidation -v`: OK, 6 tests.
- `.venv/bin/python -m unittest tests.test_email.TestEmailService.test_send_verification_email_resend tests.test_email.TestEmailService.test_send_verification_email_sendgrid tests.test_email.TestEmailService.test_send_verification_email_smtp tests.test_email.TestEmailService.test_send_reset_password_email_resend tests.test_email.TestEmailService.test_send_reset_password_email_smtp -v`: OK, 5 tests.
- `.venv/bin/python -m unittest tests.test_puja_idempotency tests.test_subasta_stream tests.test_subasta_pagos tests.test_subasta_multas tests.test_subasta_listados_detalles tests.test_garantia_limite tests.test_seguridad_registro tests.test_flow_articulo_producto -v`: OK, 77 tests.
- `.venv/bin/python -m py_compile app/api/auth.py app/api/admin.py app/api/usuarios.py app/api/subastas.py app/api/articulos.py app/services/auth_service.py app/services/admin_service.py app/services/usuario_service.py app/services/subasta_service.py app/services/articulo_service.py app/repositories/usuario_repo.py app/repositories/subasta_repo.py app/repositories/articulo_repo.py app/repositories/puja_repo.py app/schemas/schemas.py`: OK.
- `git diff --check`: OK.
- `git diff --no-index --check /dev/null context/22_P1_6_TESTS_HARDENING_NOTES.md`: sin errores de whitespace; el exit code `1` es esperado porque compara un archivo nuevo contra `/dev/null`.
- `timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001`: startup OK y salida `124` esperada por timeout.
- Frontend `node --version`: `node: command not found`.
- Frontend `npm --version`: `npm: command not found`.
- Frontend `git diff --check`: OK.

## Riesgos / pendientes

- `TestClient` requiere revisión de versiones/tooling si el equipo quiere volver a usarlo localmente en este entorno.
- Validación frontend automática pendiente hasta contar con Node/npm.
- Cobertura frontend extensa queda fuera de P1.6.
