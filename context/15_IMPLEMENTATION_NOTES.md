# 15 · Implementation Notes

## Etapa 1 — Seguridad y registro

Fecha: 2026-06-20

## Qué se implementó

- `POST /auth/registro/paso1` ahora crea la solicitud y la deja pendiente.
- Paso 1 ya no llama a `UsuarioRepository.aprobar_registro`.
- Paso 1 ya no genera token/código de paso 2 ni envía email de aprobación.
- `POST /admin/usuarios/{id}/verificar` ahora exige admin real (`usuarioId == 1`).
- La aprobación admin exige `categoria`, setea `admitido = 'si'`, `estado_registro = 'aprobado'`, limpia `motivo_rechazo`, genera `token_email` y envía el email existente.
- El rechazo admin exige `motivoRechazo`, setea `admitido = 'no'`, `estado_registro = 'rechazado'`, guarda `motivo_rechazo`, limpia `token_email` y envía el email existente.
- Los endpoints administrativos pendientes ahora exigen admin.
- `POST /subastas/{id}/cerrar` ahora exige admin antes de ejecutar el cierre.
- El frontend de `register-step1` ya no promete que el código llega inmediatamente ni redirige automáticamente al paso 2.

## Archivos modificados

- `app/dependencies.py`
- `app/api/auth.py`
- `app/api/admin.py`
- `app/api/subastas.py`
- `app/repositories/usuario_repo.py`
- `tests/test_seguridad_registro.py`
- `context/15_IMPLEMENTATION_NOTES.md`
- `../frontend-da1/app/(auth)/register-step1.tsx`

## Fuera de alcance

- No se implementó UI admin.
- No se tocó P0.3 ni idempotencia de pujas.
- No se tocaron SSE, pagos, multas, deploy ni cierre automático.
- No se cambió el modelo de roles; admin sigue siendo `usuarioId == 1`.
- No se agregaron migraciones de DB.

## Cómo probar el flujo

1. Enviar `POST /auth/registro/paso1` con multipart (`documento`, `nombre`, `apellido`, `email`, `direccion`, `numeroPais`, `fotoFrente`, `fotoDorso`, `telefono` opcional).
2. Confirmar en DB que el usuario queda con `clientes.admitido = 'no'` y `clientes_adicionales.estado_registro = 'pendiente'`.
3. Intentar login con un usuario pendiente o rechazado: debe fallar.
4. Obtener token admin con `/auth/login` usando el usuario cuyo JWT contenga `usuarioId = 1`.
5. Aprobar o rechazar desde `/admin/usuarios/{id}/verificar`.
6. Si se aprueba, copiar el código recibido por email y completar `/auth/registro/paso2`.
7. Probar con token de usuario común en endpoints admin: debe responder `403`.

## Cómo conseguir el token admin

El backend no tiene roles todavía. El token admin es cualquier JWT emitido por `/auth/login` para el usuario cuyo `usuarioId` sea `1`.

```bash
curl --location 'http://127.0.0.1:8000/auth/login' \
  --header 'Content-Type: application/json' \
  --data '{
    "documento": "DOCUMENTO_ADMIN",
    "password": "PASSWORD_ADMIN"
  }'
```

Respuesta esperada: copiar `access_token` y usarlo como `Authorization: Bearer ADMIN_ACCESS_TOKEN`.

## Aprobar usuario pendiente

Schema real: `UsuarioVerificacion.admitido` es boolean. `categoria` acepta `comun`, `especial`, `plata`, `oro`, `platino`.

```bash
curl --location 'http://127.0.0.1:8000/admin/usuarios/ID_USUARIO/verificar' \
  --header 'Authorization: Bearer ADMIN_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "admitido": true,
    "categoria": "comun"
  }'
```

JSON para Postman:

```json
{
  "admitido": true,
  "categoria": "comun"
}
```

Categorías válidas:

```json
["comun", "especial", "plata", "oro", "platino"]
```

## Rechazar usuario pendiente

```bash
curl --location 'http://127.0.0.1:8000/admin/usuarios/ID_USUARIO/verificar' \
  --header 'Authorization: Bearer ADMIN_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "admitido": false,
    "motivoRechazo": "Documentación ilegible o datos insuficientes."
  }'
```

JSON para Postman:

```json
{
  "admitido": false,
  "motivoRechazo": "Documentación ilegible o datos insuficientes."
}
```

## Prueba de seguridad con usuario común

```bash
curl --location 'http://127.0.0.1:8000/admin/usuarios/ID_USUARIO/verificar' \
  --header 'Authorization: Bearer USER_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "admitido": true,
    "categoria": "comun"
  }'
```

Respuesta esperada:

```json
{
  "detail": "No autorizado (solo administradores)."
}
```

Status esperado: `403`.

También deben responder `403` para usuario común:

- `POST /admin/medios-pago/{id}/verificar`
- `POST /admin/articulos/{id}/evaluar`
- `POST /admin/subastas`
- `POST /admin/subastas/{id}/catalogo/items`
- `POST /subastas/{id}/cerrar`

## Errores esperados

- Aprobar sin `categoria`: `400`.
- Rechazar sin `motivoRechazo`: `400`.
- Usuario común en endpoints admin/cierre: `403`.
- Usuario inexistente al aprobar/rechazar: `404`.

## Validación ejecutada

- `.venv/bin/python -m unittest tests.test_seguridad_registro -v`: OK, 12 tests.
- `.venv/bin/python -m unittest tests.test_seguridad_registro tests.test_flow_articulo_producto tests.test_email.TestConfigValidation tests.test_email.TestEmailService.test_send_verification_email_resend tests.test_email.TestEmailService.test_send_verification_email_sendgrid tests.test_email.TestEmailService.test_send_verification_email_smtp tests.test_email.TestEmailService.test_send_reset_password_email_resend tests.test_email.TestEmailService.test_send_reset_password_email_smtp -v`: OK, 26 tests.
- `.venv/bin/python -m unittest discover -s tests -v`: no terminó limpio por deuda heredada. `test_email.TestEmailService.test_integration_real_send` falla por DNS/red al intentar SendGrid real y luego la suite queda colgada al entrar en `test_usuarios.TestUsuariosApi.test_delete_profile_picture`.
- `timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`: bloqueado por puerto ocupado al correr fuera del sandbox.
- `timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload`: OK, startup completo y apagado por timeout.
- `node --version` en `../frontend-da1`: no disponible en este entorno.

## Pendientes detectados

- `docs/Swagger_v4.YAML` todavía conserva en la respuesta `201` de `/auth/registro/paso1` la frase vieja "Se envio email para el paso 2", aunque la descripción del endpoint ya dice que queda pendiente de verificación. No se tocó Swagger en esta etapa para mantener el alcance pedido.
- Confirmar cuál es el usuario admin real en cada entorno, porque el guard actual depende de `usuarioId == 1`.
