# 18 · Deploy & Release Hardening

## 1. Objetivo

Dejar el proyecto preparado para la entrega final desde el punto de vista operativo: backend deployable y verificable en Render, frontend Expo apuntando al backend online cuando se prueba desde dispositivo, variables documentadas sin secretos, smoke tests claros y checklist de entrega.

## 2. Estado actual

- El backend es FastAPI y usa Docker para Render. No hay `render.yaml` en este repo; el deploy depende del `Dockerfile` y de variables cargadas en el dashboard de Render.
- El `Dockerfile` usa `python:3.12-slim`, instala `requirements.txt` y arranca `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`. Esto es compatible con Render porque Render inyecta `$PORT`.
- El frontend es Expo / React Native y consume la API por Axios desde `EXPO_PUBLIC_API_URL`.
- El backend usa Supabase/PostgreSQL y Supabase Storage. Buckets esperados: `documentos` para DNI/perfil/articulos via `StorageService`, e `imagenes` para presigned uploads.
- El email es configurable por `EMAIL_PROVIDER`. Produccion esta documentada con SendGrid (`EMAIL_PROVIDER=sendgrid` + `EMAIL_API_KEY`); SMTP queda como alternativa local.
- P0.1 y P0.2 ya fueron implementados: registro paso 1 queda pendiente y endpoints admin/cierre quedan protegidos.
- P0.3, P0.4, P0.5 y P0.6 estan en paralelo y quedan fuera de alcance de esta rama.
- `app/config.py` ahora soporta `APP_ENV`. En `APP_ENV=production` el backend falla en startup si `SECRET_KEY` falta o conserva el default inseguro.

## 3. Variables de entorno backend

| Variable | Requerida local | Requerida produccion | Ejemplo placeholder | Notas |
|---|---:|---:|---|---|
| `APP_ENV` | No | Si | `development` / `production` | Default local: `development`. En Render usar `production`. |
| `DATABASE_URL` | Si | Si | `postgresql://USER:PASSWORD@HOST:PORT/DBNAME` | Connection string de Supabase/PostgreSQL. En Render conviene usar el pooler. |
| `SUPABASE_URL` | Si | Si | `https://PROJECT.supabase.co` | URL base del proyecto Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` | Si | Si | `SUPABASE_SERVICE_ROLE_KEY_HERE` | Solo backend. Nunca usar en frontend. |
| `SECRET_KEY` | Recomendado | Si | `CHANGE_ME_TO_A_LONG_RANDOM_SECRET` | Firma JWT. En produccion no puede ser el default. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | No | `30` | Default: `30`. |
| `EMAIL_PROVIDER` | No | Si | `sendgrid` | Valores soportados: `smtp`, `resend`, `sendgrid`. Default codigo: `smtp`. |
| `EMAIL_API_KEY` | Condicional | Si si provider API | `SENDGRID_API_KEY_HERE` | Requerida para `resend` o `sendgrid`. |
| `EMAIL_FROM` | No | Recomendado | `no-reply@example.com` | Remitente; SendGrid puede exigir remitente verificado. |
| `SMTP_HOST` | Condicional | No si SendGrid | `smtp.gmail.com` | Requerida solo si `EMAIL_PROVIDER=smtp`. |
| `SMTP_PORT` | Condicional | No si SendGrid | `587` | Requerida solo si `EMAIL_PROVIDER=smtp`. |
| `SMTP_USER` | Condicional | No si SendGrid | `user@example.com` | Requerida solo si `EMAIL_PROVIDER=smtp`. |
| `SMTP_PASSWORD` | Condicional | No si SendGrid | `SMTP_PASSWORD_HERE` | Requerida solo si `EMAIL_PROVIDER=smtp`. |

Notas:

- `app/config.py` valida email en startup. Si `EMAIL_PROVIDER=smtp`, faltan `SMTP_USER` o `SMTP_PASSWORD`, la API no arranca.
- Si `EMAIL_PROVIDER=resend` o `sendgrid`, falta `EMAIL_API_KEY`, la API no arranca.
- `backend-da1/.env.example` tiene placeholders versionables. El `.env` real sigue ignorado por git.

## 4. Variables de entorno frontend

| Variable | Requerida local | Requerida produccion/dispositivo | Ejemplo placeholder | Notas |
|---|---:|---:|---|---|
| `EXPO_PUBLIC_API_URL` | Si | Si | `https://backend-da1.onrender.com` | Expo expone toda variable `EXPO_PUBLIC_*` dentro de la app. No poner secretos aca. |

Uso esperado:

- Local web o emulador en la misma maquina: `http://localhost:8000` puede servir.
- Celular fisico: `localhost` apunta al telefono, no a la notebook. Usar el backend online de Render o una IP LAN tipo `http://192.168.X.X:8000`.
- Produccion/demo: usar la URL final de Render.
- Al cambiar `.env` en Expo, reiniciar el servidor de Expo para que tome la variable.

## 5. Checklist Render

1. Crear un Web Service desde el repo `backend-da1`.
2. Runtime: Docker.
3. Verificar que el comando del contenedor use `$PORT`; el `Dockerfile` actual ya lo hace.
4. Cargar variables en Environment.
5. No subir `.env`.
6. Setear `APP_ENV=production`.
7. Setear `SECRET_KEY` real, largo y distinto de `your-secret-key-change-in-production`.
8. Confirmar `DATABASE_URL`, `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY`.
9. Confirmar SendGrid o provider real: `EMAIL_PROVIDER=sendgrid`, `EMAIL_API_KEY`, `EMAIL_FROM`.
10. Deploy.
11. Probar `GET /`.
12. Probar `/docs` en navegador.

## 6. Checklist Supabase

- Confirmar que la DB es accesible desde Render.
- Confirmar connection string pooler de Supabase para `DATABASE_URL`.
- Confirmar buckets `documentos` e `imagenes`.
- Confirmar que `SUPABASE_SERVICE_ROLE_KEY` se carga solo en backend.
- Confirmar que el frontend nunca usa service role key.
- Confirmar si hay migraciones pendientes antes de tocar schema.
- Confirmar el proceso real de migraciones. Hoy hay SQL plano y `docs/run_migration.py`, pero no Alembic ni framework formal.

## 7. Checklist Expo / dispositivo

- Configurar `EXPO_PUBLIC_API_URL` con el backend online para celular fisico.
- Reiniciar Expo despues de cambiar `.env`.
- Probar desde celular fisico, no solo web.
- Evitar `localhost` en celular fisico.
- Scripts disponibles en `package.json`: `npm start`, `npm run android`, `npm run ios`, `npm run web`, `npm run lint`.
- No hay script `typecheck` en `package.json`; no inventarlo para la validacion.

## 8. Smoke tests locales

Base local:

```bash
export BASE_URL="http://127.0.0.1:8000"
```

Health:

```bash
curl -i "$BASE_URL/"
```

Swagger:

```bash
curl -I "$BASE_URL/docs"
```

Login:

```bash
curl -i -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"documento":"DOCUMENTO_ADMIN_O_USUARIO","password":"PASSWORD"}'
```

Perfil autenticado:

```bash
curl -i "$BASE_URL/usuarios/me" \
  -H "Authorization: Bearer USER_TOKEN"
```

Subastas publicas:

```bash
curl -i "$BASE_URL/subastas/publicas"
```

Registro paso 1 pendiente:

```bash
curl -i -X POST "$BASE_URL/auth/registro/paso1" \
  -F "documento=DOCUMENTO_NUEVO" \
  -F "nombre=Nombre" \
  -F "apellido=Apellido" \
  -F "email=persona@example.com" \
  -F "direccion=Direccion 123" \
  -F "numeroPais=1" \
  -F "fotoFrente=@/ruta/a/frente.png" \
  -F "fotoDorso=@/ruta/a/dorso.png"
```

Aprobacion admin de P0.2:

```bash
curl -i -X POST "$BASE_URL/admin/usuarios/ID_USUARIO/verificar" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"admitido":true,"categoria":"comun"}'
```

Tambien se agregaron scripts no destructivos:

```bash
BASE_URL="http://127.0.0.1:8000" scripts/smoke_local.sh
```

## 9. Smoke tests online

Base online actual documentada:

```bash
export BASE_URL="https://backend-da1.onrender.com"
```

Repetir los mismos comandos de la seccion local cambiando solo `BASE_URL`.

Script online:

```bash
BASE_URL="https://backend-da1.onrender.com" scripts/smoke_online.sh
```

## 10. Tests automatizados

Comandos seguros para P0.7:

```bash
source .venv/bin/activate
python -m unittest tests.test_seguridad_registro -v
python -m unittest tests.test_flow_articulo_producto -v
python -m unittest tests.test_email.TestConfigValidation -v
```

Startup local:

```bash
timeout 8s .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Suite completa:

```bash
python -m unittest discover -s tests -v
```

Deuda heredada conocida segun `15_IMPLEMENTATION_NOTES.md`:

- `test_email.TestEmailService.test_integration_real_send` puede fallar por DNS/red al intentar SendGrid real.
- La suite completa puede colgar al entrar en `test_usuarios.TestUsuariosApi.test_delete_profile_picture`.
- Esto se documenta como deuda heredada, no como error de P0.7.

## 11. Checklist anti-secretos

- Revisar `git status` antes de cerrar.
- Confirmar `.env` ignorado en backend y frontend.
- Buscar patrones antes de commitear: `DATABASE_URL=`, `SUPABASE_SERVICE_ROLE_KEY`, `EMAIL_API_KEY`, `SMTP_PASSWORD`, `SECRET_KEY`.
- No pegar valores reales en docs, Swagger, scripts ni screenshots.
- No versionar `.env`.
- Rotar secretos si circularon fuera de canales seguros.

## 12. Checklist final de entrega

- [ ] Backend online responde `/`.
- [ ] `/docs` accesible.
- [ ] Frontend apunta a backend online.
- [ ] Login funciona.
- [ ] Registro paso 1 queda pendiente.
- [ ] Admin aprueba usuario.
- [ ] Usuario aprobado completa paso 2.
- [ ] Usuario comun no puede endpoints admin.
- [ ] Sin secretos versionados.
- [ ] Tests minimos pasan.
- [ ] P0.3-P0.6 documentados como fuera de alcance de esta rama porque estan en paralelo.

## 13. Fuera de alcance

- No se implemento P0.3.
- No se implemento P0.4.
- No se implemento P0.5.
- No se implemento P0.6.
- No se toco logica de negocio de subastas.
- No se agrego UI admin.
- No se cambio modelo de roles.
- No se tocaron pujas, SSE, pagos, multas ni cierre de negocio salvo smoke/documentacion.

## 14. Pendientes para el equipo

- Confirmar usuario admin real en cada entorno; el guard actual depende de `usuarioId == 1`.
- Confirmar URL final de Render. Este documento usa `https://backend-da1.onrender.com` porque ya estaba documentada.
- Confirmar claves rotadas antes de exposicion publica.
- Confirmar un solo worker en Render si SSE sigue en memoria.
- Confirmar migraciones pendientes y proceso oficial para aplicarlas.
- Confirmar si Swagger debe regenerarse completo mas adelante. En esta rama solo se corrige la frase vieja de `/auth/registro/paso1` para alinear P0.1.
- Confirmar si `CORS allow_origins=["*"]` se mantiene para la entrega o se acota en produccion.
