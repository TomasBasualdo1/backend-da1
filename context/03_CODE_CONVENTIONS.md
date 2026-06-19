# 03 · Convenciones de código

Basadas en el código real del repo. Para escribir código nuevo, **imitá el archivo vecino de la misma capa**.

## Idioma

- **Dominio en español**: nombres de entidades, rutas y mensajes de error al usuario (`Subasta`, `Articulo`, `Puja`, "Subasta no encontrada").
- **Infraestructura en inglés**: `get_db`, `get_current_user`, `create_access_token`, `Service`, `Repository`.
- Nombres de funciones de endpoint en inglés (`place_bid`, `list_auctions`); rutas en español (`/subastas`, `/pujar`).

## Capas y nombres de archivo

| Capa | Carpeta | Naming | Patrón |
|------|---------|--------|--------|
| Router | `app/api/` | `<recurso>.py` (plural, español) | `router = APIRouter(prefix="/<recurso>")`, funciones `async def` |
| Service | `app/services/` | `<entidad>_service.py` | `class <Entidad>Service:` con `@staticmethod` |
| Repository | `app/repositories/` | `<entidad>_repo.py` | `class <Entidad>Repository:` con `@staticmethod` |
| Schemas | `app/schemas/schemas.py` | archivo único | Clases Pydantic (no crear archivos nuevos salvo necesidad) |

> Services y repositories son **clases con métodos estáticos** (no se instancian). Se llaman como `SubastaService.procesar_puja(db, ...)`. Mantené ese estilo.

## Routers (`app/api/`)

- Firma típica: `async def handler(..., db: Connection = Depends(get_db), user: dict = Depends(get_current_user))`.
- Endpoints públicos: omiten `get_current_user` (ej. `/subastas/publicas`, `/paises`).
- Declarar `response_model=` y `status_code=` cuando aplique.
- Body: usar modelos Pydantic; para multipart usar `Form(...)`/`File(...)`.
- El `user` (dict del JWT) trae `usuarioId`, `categoria`, `admitido`, `jti`, `exp`.
- Admin: llamar `_require_admin(user)` (chequea `usuarioId == 1`).
- Registrar el router nuevo en `app/api/router.py` con su `tags`.

## Services

- Reciben `db: Connection` como primer parámetro.
- Contienen las reglas de negocio y lanzan `HTTPException(status_code=..., detail="...")` con códigos correctos (400/401/403/404/409).
- **Hacen `db.commit()`** tras operaciones de escritura (no lo hace el repo).
- Delegan toda persistencia al repository.

## Repositories

- SQL crudo con `with db.cursor() as cursor:` y `cursor.execute(query, params)`.
- **Siempre** queries parametrizadas con `%s` (nunca f-strings con datos de usuario → SQL injection).
- Devuelven `dict` / `list[dict]` (cursor con `dict_row`).
- Para que el response Pydantic camelCase funcione, aliasar columnas: `SELECT fecha_hora as "fechaHora"`.
- No lanzan reglas de negocio (eso es del service); sí pueden hacer validaciones de existencia mínimas.

## Mapeo BD ↔ API

- Columnas en BD: `snake_case` (`estado_verificacion`, `cliente_id`).
- Campos en schemas/JSON: mayormente `camelCase` (`estadoVerificacion`) y a veces snake (`ultimos_digitos`, `datos_encriptados`). **No asumir**: verificar el modelo en `schemas.py`.
- Enums de dominio están en `schemas.py` como `Enum` (ojo con los nombres autogenerados: `Estado1`, `Estado2`, `Tipo2`, etc.).

## Errores HTTP (convención observada)

| Código | Uso |
|--------|-----|
| 400 | Validación de negocio (monto fuera de rango, falta dato) |
| 401 | Token inválido/expirado/revocado |
| 403 | Sin permiso (categoría insuficiente, no admin, bloqueado) |
| 404 | Recurso inexistente |
| 409 | Conflicto (ya conectado a otra subasta) |

## Estilo Python

- Type hints en firmas (`db: Connection`, `-> dict`).
- Imports agrupados: stdlib → terceros → `app.*`.
- f-strings para mensajes; nunca para SQL con datos externos.
- La indentación del repo es de 4 espacios; algunos archivos viejos (`dependencies.py`, `auth_service.py`) tienen indentación de 2 espacios — al editarlos, respetá la del archivo.
