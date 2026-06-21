# 04 · AI Workflow

Cómo debe trabajar una IA (o dev nuevo) en este repo **antes de tocar código**.

## 1. Cargar contexto (en este orden)

1. [00_OVERVIEW.md](00_OVERVIEW.md) y [01_ARCHITECTURE.md](01_ARCHITECTURE.md) — modelo mental.
2. [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md) — reglas de negocio (no inventarlas).
3. Para tareas de datos: [11_DATABASE.md](11_DATABASE.md) + `db/Estructura-PostgreSQL-da1-updated.sql`.
4. Para tareas de API: [10_API_REFERENCE.md](10_API_REFERENCE.md) + `docs/Swagger_v4.YAML` + `app/schemas/schemas.py`.
5. El **archivo vecino** de la capa que vas a tocar (imitar su estilo).

## 2. Qué leer según el tipo de tarea

| Tarea | Leé primero |
|-------|-------------|
| Nuevo endpoint | router del mismo recurso → service → repo + `schemas.py` + Swagger |
| Cambiar regla de negocio | el `*_service.py` correspondiente + [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md) |
| Query / dato nuevo | el `*_repo.py` + el SQL en `db/` + [11_DATABASE.md](11_DATABASE.md) |
| Auth / permisos | `core/security.py`, `dependencies.py`, `services/auth_service.py` |
| Subastas / pujas / cierre | `services/subasta_service.py`, `repositories/subasta_repo.py`, `services/streamer.py` |
| Consignación de artículos | `services/articulo_service.py`, `repositories/articulo_repo.py`, [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md) §flujo |
| Storage / fotos | `services/storage_service.py`, `api/uploads.py` |
| Email | `services/email_service.py`, config en `config.py` |

## 3. Cómo investigar una feature

1. Buscá el endpoint en `app/api/router.py` → archivo del router.
2. Seguí la cadena router → service → repository.
3. Cruzá con `schemas.py` para el contrato y con `db/*.sql` para las columnas reales.
4. Verificá si el frontend ya lo consume (`frontend-da1/src/services/*.ts`) — ver [12_INTEGRATION.md](12_INTEGRATION.md).

## 4. No asumir (verificar en código)

- **Nombres de columnas**: snake_case en BD; no asumir camelCase. Mirá el `.sql`.
- **Nombres de campos JSON**: mezcla camel/snake. Mirá `schemas.py`.
- **Quién commitea**: el commit lo hace el service/endpoint, no el repo.
- **Quién es admin**: hoy es `usuarioId == 12`, no un rol.
- **Si una columna existe**: el `.sql` es snapshot; confirmá contra la BD real si vas a depender de algo nuevo.
- **Tablas duales**: hay `productos`/`fotos` (legado, sistema de la empresa) **y** `articulos`/`fotos_adicionales` (consignación nueva). No confundirlas — ver [11_DATABASE.md](11_DATABASE.md).

## 5. No romper arquitectura

- Respetá Controller → Service → Repository. No metas SQL nuevo en routers (aunque existan casos viejos).
- No instancies services/repos: son métodos estáticos.
- No cambies el contrato (`schemas.py` / Swagger) sin actualizar **ambos** lados y dejar nota.
- No agregues un ORM ni cambies psycopg sin acuerdo explícito.
- SSE es en memoria y mono-worker: no asumas que escala.

## 6. Checklist previo a cualquier cambio

- [ ] ¿Identifiqué la capa correcta (router/service/repo)?
- [ ] ¿Hay un endpoint/regla equivalente que pueda imitar?
- [ ] ¿El contrato (Swagger/schemas) ya define esto? ¿Lo respeto exactamente?
- [ ] ¿Las queries son parametrizadas (`%s`)?
- [ ] ¿Hace falta `db.commit()`?
- [ ] ¿Los códigos HTTP son los correctos (400/401/403/404/409)?
- [ ] ¿Afecta al frontend? ¿Hay que avisar/ajustar `frontend-da1`?
- [ ] ¿Registré el router nuevo en `router.py`?
- [ ] ¿Actualicé `progress-tracker.md` / specs si corresponde?

## 7. Convención SDD heredada (specs)

El proyecto venía trabajando con **Spec-Driven Development**: specs numeradas en `frontend-da1/context/specs/` y un `progress-tracker.md`. Si trabajás una feature grande, fijate si tiene spec asociada y mantené el tracker. No es obligatorio para fixes chicos.
