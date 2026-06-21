# 01 · Arquitectura

## Patrón general: arquitectura en capas (Controller → Service → Repository)

```
HTTP request
   │
   ▼
app/api/*.py          (Routers / "controllers")
   │   - definen rutas, status codes, response_model
   │   - parsean body/form/query, inyectan get_db y get_current_user
   ▼
app/services/*.py     (Business logic)
   │   - reglas de negocio, validaciones de dominio, orquestación
   │   - lanzan HTTPException con códigos correctos
   ▼
app/repositories/*.py (Data access)
   │   - SQL crudo con psycopg3 (cursores, dict_row)
   │   - sin reglas de negocio: solo persistencia/consultas
   ▼
PostgreSQL (Supabase)
```

**Regla de capas (respetar siempre):**
- Los **routers** no deberían tener SQL salvo casos puntuales ya existentes (ej. `notificaciones.py`, partes de `usuarios.py` y `auth.py` hacen SQL inline — es deuda técnica, no el patrón ideal). Para código nuevo: router delgado → service → repository.
- Los **services** no abren conexiones ni conocen FastAPI más allá de `HTTPException`.
- Los **repositories** no validan reglas de negocio.

## Flujo de datos típico (ejemplo: pujar)

1. `POST /subastas/{id}/items/{item_id}/pujar` → `app/api/subastas.py:place_bid`
2. Inyecta `get_current_user` (decodifica JWT, valida blacklist) y `get_db`.
3. Llama `SubastaService.procesar_puja(...)` → valida asistente, bloqueos, mínimos/máximos (1%/20%), registra puja, `db.commit()`.
4. El router hace `await SubastaStreamer.broadcast(id, "puja", {...})` para notificar por SSE.
5. Devuelve `PujaResponse`.

## Directorios y archivos críticos

| Archivo | Rol |
|---------|-----|
| `main.py` | Crea la app, CORS abierto (`allow_origins=["*"]`), monta `app.api.router`. |
| `app/api/router.py` | Agrega todos los routers con sus `tags`. Punto único de registro. |
| `app/config.py` | `Settings` (pydantic-settings). Lee `.env`. Valida config de email. Exporta `settings`. |
| `app/core/database.py` | `get_db_connection()` context manager. Conexión psycopg con `dict_row`. **Una conexión por request.** |
| `app/core/security.py` | Hash/verify password (bcrypt), crear/decodificar JWT (HS256, claim `jti` para blacklist). |
| `app/dependencies.py` | `get_db()` (yield conn) y `get_current_user()` (decodifica token + chequea blacklist). |
| `app/services/streamer.py` | `SubastaStreamer`: singleton en memoria con colas asyncio por subasta para SSE. |
| `app/schemas/schemas.py` | Todos los modelos Pydantic (request/response). Generados desde el Swagger. |

## Patrones y decisiones detectadas

- **SQL crudo, sin ORM.** Se usa `psycopg3` con `row_factory=dict_row`. Las filas son `dict`. Las queries seleccionan con alias en `camelCase` cuando el response Pydantic lo espera (ej. `fecha_hora as "fechaHora"`).
- **Transacciones manuales.** El service hace `db.commit()` explícito. La conexión se cierra en el `finally` de `get_db_connection`. **No hay autocommit.** Si olvidás `commit()`, los cambios se pierden.
- **Auth stateless + blacklist.** JWT firmado HS256 con `jti`. El logout inserta el `jti` en `blacklisted_tokens`; `get_current_user` rechaza tokens en blacklist. Claims del token: `usuarioId`, `categoria`, `admitido`, `exp`, `jti`.
- **Admin = usuario id 12.** No hay tabla de roles para la API: el chequeo de admin es `user.get("usuarioId") != 12` (`app/api/admin.py:_require_admin`). Decisión simplificada; ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md).
- **SSE en memoria (no persistente).** `SubastaStreamer._listeners` es un dict en memoria del proceso. No sobrevive reinicios ni escala horizontalmente (multiworker rompería el broadcast). Adecuado para 1 worker.
- **Storage vía Supabase.** `StorageService.upload_file` hace PUT directo al bucket `documentos`. `uploads.py` también ofrece presigned URLs sobre el bucket `imagenes`.
- **Doble esquema de modelos.** `app/schemas/schemas.py` está autogenerado desde `Swagger_v4.YAML` (incluye nombres como `Estado1`, `Tipo2` por el codegen). Los repositorios mapean nombres de columnas snake_case del SQL a los campos camelCase de los schemas.

## Concurrencia / motor de pujas

El Swagger y los docs previos mencionan `Idempotency-Key` y pessimistic locking. Estado **real** en el código:
- **Pessimistic locking: SÍ implementado.** `SubastaRepository.get_item_for_update` (`subasta_repo.py:441`) hace `SELECT ... FOR UPDATE OF ic` sobre el ítem, serializando pujas concurrentes sobre el mismo ítem dentro de la transacción.
- **Idempotency-Key: NO implementado en backend.** El frontend envía el header en `pujar()`, pero ningún endpoint lo lee ni deduplica. Es deuda pendiente (ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md)).
