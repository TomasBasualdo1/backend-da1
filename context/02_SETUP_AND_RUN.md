# 02 · Setup & Run

## Requisitos

- Python 3.12+
- Acceso a una base de datos PostgreSQL (Supabase) ya provisionada con el esquema de `db/Estructura-PostgreSQL-da1-updated.sql`.
- Credenciales de Supabase (URL + service role key) y de un proveedor de email.

## Instalar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> El venv se llama `.venv` (gitignored). Activarlo antes de instalar o correr.

## Variables de entorno (`.env` en la raíz del repo)

Leídas por `app/config.py` (`Settings`, pydantic-settings, `env_file=".env"`). Los nombres en `.env` son **case-insensitive** respecto de los campos.

| Variable | Requerida | Default | Notas |
|----------|-----------|---------|-------|
| `DATABASE_URL` | **Sí** | — | Cadena de conexión psycopg a Postgres/Supabase. |
| `SUPABASE_URL` | **Sí** | — | Base URL del proyecto Supabase (para Storage). |
| `SUPABASE_SERVICE_ROLE_KEY` | **Sí** | — | Service role key (subida de archivos / presign). |
| `SECRET_KEY` | No | `your-secret-key-change-in-production` | Clave de firma JWT. **Cambiar en prod.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Expiración del JWT. |
| `EMAIL_PROVIDER` | No | `smtp` | `smtp` \| `resend` \| `sendgrid`. |
| `SMTP_HOST` / `SMTP_PORT` | No | `smtp.gmail.com` / `587` | Si provider = smtp. |
| `SMTP_USER` / `SMTP_PASSWORD` | Condicional | — | **Requeridas si `EMAIL_PROVIDER=smtp`** (valida `config.py`). |
| `EMAIL_API_KEY` | Condicional | — | **Requerida si provider = resend/sendgrid.** |
| `EMAIL_FROM` | No | — | Remitente. |

> `app/config.py` **falla al arrancar** (`ValueError`) si la config de email no es coherente con el provider. Si solo querés levantar la API sin email real, igual necesitás `SMTP_USER`/`SMTP_PASSWORD` (o cambiar el provider y dar `EMAIL_API_KEY`).

## Correr local

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- App: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

> **Windows**: borrar `uvloop==0.22.1` de `requirements.txt` antes de instalar (uvloop no soporta Windows).

> **El backend ya está deployado** en `https://backend-da1.onrender.com`. Solo se corre local para **modificar/agregar endpoints y testear** antes de subir. El frontend de dev por defecto apunta al backend de Render (ver su `02_SETUP_AND_RUN.md`).
>
> **Valores reales de `.env`**: los provee el equipo (están en Notion). El provider de email en producción es **`sendgrid`** (`EMAIL_PROVIDER=sendgrid` + `EMAIL_API_KEY`), no SMTP. La DB es un pooler de Supabase (`...pooler.supabase.com:5432`). Ver [13_SECURITY.md](13_SECURITY.md) sobre manejo de estos secretos.

## Docker / Deploy

`Dockerfile` usa `python:3.12-slim`, instala `requirements.txt`, copia el código y arranca:
```
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```
Pensado para **Render** (inyecta `$PORT`). El frontend de producción apunta a un host tipo `backend-da1.onrender.com`.

## Servicios externos requeridos

- **Supabase**: PostgreSQL (datos) + Storage (buckets `documentos` e `imagenes` para fotos de DNI, perfil y artículos).
- **Proveedor de email**: SMTP (Gmail por defecto), Resend o SendGrid — para verificación de cuenta, rechazo y reset de password.
- **Sentry** (`sentry-sdk` está en `requirements.txt`): PENDIENTE DE CONFIRMAR si está inicializado; no se vio `sentry_sdk.init()` en el código revisado.

## Migraciones / Seeds

No hay framework de migraciones (Alembic, etc.). El esquema se administra como SQL plano:
- `db/Estructura-PostgreSQL-da1-updated.sql` — esquema actual (snapshot; el header dice "for context only, not meant to be run").
- `db/seed_subastas_demo.sql` — datos demo de subastas.
- `db/rollback_seed_subastas_demo.sql` — revierte el seed demo.
- `docs/run_migration.py` — script auxiliar de migración (revisar antes de usar).

## Problemas comunes detectables desde el repo

- **App no arranca**: casi siempre por `.env` (faltan `DATABASE_URL`/Supabase, o email mal configurado → `ValueError` en `Settings`).
- **401 en endpoints protegidos**: token ausente/expirado o en `blacklisted_tokens` (post-logout).
- **403 "solo administradores"**: la acción requiere ser `usuarioId == 12`.
- **Cambios que "no se guardan"**: falta `db.commit()` en el service/endpoint (no hay autocommit).
- **CORS**: está abierto a todo (`allow_origins=["*"]`); no debería dar problemas en dev.
