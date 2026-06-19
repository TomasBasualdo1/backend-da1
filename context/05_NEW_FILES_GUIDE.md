# 05 · Guía para crear archivos nuevos

## Árbol de decisión rápido

| Quiero… | Creo / edito |
|---------|--------------|
| Un nuevo grupo de endpoints (recurso nuevo) | `app/api/<recurso>.py` + registrarlo en `app/api/router.py` |
| Un endpoint en un recurso existente | editar el `app/api/<recurso>.py` que corresponda |
| Lógica de negocio nueva | `app/services/<entidad>_service.py` (nuevo) o método en uno existente |
| Acceso a datos nuevo | método en `app/repositories/<entidad>_repo.py` (o archivo nuevo) |
| Modelo request/response | clase nueva en `app/schemas/schemas.py` |
| Utilidad de seguridad / DB | `app/core/` |

## Crear un recurso nuevo (full stack interno)

Supongamos `reportes`. Archivos que típicamente cambian **juntos**:

1. **`app/schemas/schemas.py`** — modelos `ReporteCreate`, `Reporte`, etc.
2. **`app/repositories/reporte_repo.py`**:
   ```python
   from psycopg import Connection

   class ReporteRepository:
       @staticmethod
       def get_all(db: Connection) -> list[dict]:
           with db.cursor() as cursor:
               cursor.execute("SELECT ... FROM reportes")
               return cursor.fetchall()
   ```
3. **`app/services/reporte_service.py`**:
   ```python
   from fastapi import HTTPException
   from psycopg import Connection
   from app.repositories.reporte_repo import ReporteRepository

   class ReporteService:
       @staticmethod
       def listar(db: Connection) -> list[dict]:
           return ReporteRepository.get_all(db)
   ```
4. **`app/api/reportes.py`**:
   ```python
   from fastapi import APIRouter, Depends
   from psycopg import Connection
   from app.dependencies import get_db, get_current_user
   from app.services.reporte_service import ReporteService

   router = APIRouter(prefix="/reportes")

   @router.get("")
   async def list_reportes(db: Connection = Depends(get_db), user: dict = Depends(get_current_user)):
       return ReporteService.listar(db)
   ```
5. **`app/api/router.py`** — agregar:
   ```python
   from app.api.reportes import router as reportes_router
   router.include_router(reportes_router, tags=["Reportes"])
   ```

## Naming

- Routers: plural en español (`reportes.py`), `prefix="/reportes"`.
- Service/Repo: singular + sufijo (`reporte_service.py`, `reporte_repo.py`), clases `ReporteService` / `ReporteRepository`.
- Funciones de endpoint: verbo en inglés (`list_reportes`, `create_reporte`).

## Imports/exports a actualizar al agregar cosas

- Router nuevo → **siempre** registrarlo en `app/api/router.py` (si no, no existe).
- Schema nuevo → importarlo donde se use (no hay `__all__`; import explícito por clase).
- Service que usa otro service → import directo (ej. `AdminService` importa `SubastaService`).

## Patrones a copiar según el caso

| Caso | Copiá de |
|------|----------|
| Endpoint autenticado simple | `app/api/subastas.py` (listados) |
| Endpoint admin | `app/api/admin.py` (`_require_admin`) |
| Multipart con archivos | `app/api/articulos.py` / `auth.py:registro_paso1` |
| Endpoint público | `app/api/paises.py` / `subastas.py:list_public_auctions` |
| Service con reglas + commit | `app/services/subasta_service.py` |
| Repo con SQL + alias camelCase | `app/repositories/subasta_repo.py` |
| SSE / tiempo real | `app/services/streamer.py` + `subastas.py:stream_auction` |

## Tests

Si agregás lógica relevante, añadí un test en `tests/` imitando `tests/test_flow_articulo_producto.py` (mockea la DB con `MagicMock`, no requiere Postgres real). Ver [06_TESTING_AND_VALIDATION.md](06_TESTING_AND_VALIDATION.md).
