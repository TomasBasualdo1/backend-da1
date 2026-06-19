# 13 · Security

Notas de seguridad **operativa**. Este archivo **no contiene secretos**; documenta cómo se manejan.

## ⚠ Secretos expuestos (acción recomendada)

Las credenciales reales de `.env` (DB de Supabase, `SUPABASE_SERVICE_ROLE_KEY`, `SMTP_PASSWORD`, `EMAIL_API_KEY` de SendGrid) **circulan en texto plano en el Notion del equipo** y fueron compartidas en chat. Riesgos:

- El **service role key de Supabase** otorga acceso total a Storage y a la base (bypassa RLS). Si se filtra, alguien puede leer/borrar datos y archivos.
- La **cadena `DATABASE_URL`** incluye usuario y contraseña del pooler de Postgres.
- La **API key de SendGrid** permite enviar correo en nombre del dominio.

**Recomendaciones:**
1. **Rotar** estas claves antes de cualquier exposición pública del repo o entrega (Supabase: regenerar service role key; SendGrid: nueva API key; Postgres: cambiar password del rol).
2. Mantener `.env` **fuera de git** (ya está en `.gitignore`) y nunca pegarlo en archivos versionados (incluida esta carpeta `context/`).
3. Para compartir entre el equipo, usar un gestor de secretos o el Notion privado — no el código.
4. En Render, cargar los secretos como **environment variables del servicio**, no en el repo.

> Por esto, ninguna doc de `context/` incluye valores de secretos: solo los **nombres** de las variables (ver [02_SETUP_AND_RUN.md](02_SETUP_AND_RUN.md)).

## Variables sensibles (solo nombres)

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SECRET_KEY` (firma JWT), `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_API_KEY`, `EMAIL_FROM`. Detalle en [02_SETUP_AND_RUN.md](02_SETUP_AND_RUN.md).

## Hallazgos de seguridad en código (resumen; detalle en 08)

| Tema | Estado |
|------|--------|
| `SECRET_KEY` con default inseguro en `config.py` | Cambiar por env en prod |
| CORS `allow_origins=["*"]` + `allow_credentials=True` | Acotar orígenes en prod |
| Autorización admin inconsistente (solo `evaluar artículo` valida) | Agregar `_require_admin` a todos los `/admin/*` y a `/cerrar` |
| Admin = `usuarioId == 1` hardcodeado | Modelar rol real |
| Registro auto-aprobado | Desacoplar (ver [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md) / [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md)) |
| `medios_pago.datos_encriptados` se guarda sin cifrado real | Revisar |
| JWT HS256 + blacklist de `jti` en logout | OK (correcto) |
| Passwords con bcrypt | OK (correcto) |

## Usuario de prueba

Existe un usuario QA de prueba (documento `224701`). Las credenciales están en el Notion del equipo; **no se versionan aquí**. Útil para smoke tests del flujo autenticado contra el backend de Render.
