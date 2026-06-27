# 27 · Subastas sin restricción de antelación de fecha

**Fecha del cambio:** 2026-06-27

## Qué se cambió

Antes una subasta solo podía crearse con **fecha posterior a hoy + 10 días**. Esa restricción se **eliminó por completo**: ahora se puede crear una subasta para **cualquier fecha, sin restricción de antelación** (incluso para hoy o fechas pasadas).

## Por qué

La regla de "≥ hoy + 10 días" bloqueaba poder mostrar el núcleo del TPO (subasta en vivo / puja dinámica ascendente en tiempo real) desde la app, porque la "sala en vivo" del frontend se gatea por `fecha == hoy` y ninguna subasta podía tener fecha de hoy. Ver el hallazgo A1 en [26_AUDITORIA_POST_BACKLOG_CONSIGNA.md](26_AUDITORIA_POST_BACKLOG_CONSIGNA.md).

## Dónde estaba la restricción (3 capas) y qué se hizo

| Capa | Antes | Después |
|------|-------|---------|
| **Backend** — [app/services/subasta_service.py](../app/services/subasta_service.py) `create_subasta` | Calculaba `min_fecha = date.today() + timedelta(days=10)` y lanzaba `400` si `fecha <= min_fecha`. | Validación eliminada; `create_subasta` delega directo en el repositorio. Se limpió el import `date, timedelta` ya sin uso. |
| **Base de datos** — tabla `subastas` | CHECK anónimo `fecha > (CURRENT_DATE + '10 days')::date`. | Se droppea con [db/migration_remove_subastas_fecha_check.sql](../db/migration_remove_subastas_fecha_check.sql) (busca el constraint por definición y lo elimina). |
| **Frontend** — [frontend-da1/app/admin/auctions.tsx](../../frontend-da1/app/admin/auctions.tsx) | `handleCreateAuction` rechazaba fechas `<= hoy+10d` con `Alert`; texto de ayuda "Debe ser posterior a 10 días". | Se removió la validación JS; el texto de ayuda ahora dice "Podés crear la subasta para cualquier fecha". |

> ⚠ **Acción de deploy requerida:** correr `db/migration_remove_subastas_fecha_check.sql` en Supabase/PostgreSQL. Sin eso, el CHECK de la BD seguiría rechazando inserts con fecha cercana aunque el backend ya no valide. El snapshot `db/Estructura-PostgreSQL-da1-updated.sql` no muestra el CHECK, pero la BD viva (según docs y seed) lo tiene; la migración es idempotente y no falla si ya no existe.

## Impacto en la demo

Ahora se puede crear con `POST /admin/subastas` una subasta con `fecha` = hoy (y `hora` ya pasada) para que la app la considere "en vivo" y se pueda pujar desde la app, no solo desde Swagger. Ver [GUIA_DEMO_SWAGGER.md](GUIA_DEMO_SWAGGER.md).

## Tests

No había tests que verificaran el rechazo de la regla de 10 días, así que no se rompió ninguno. `test_modelos_contrato` (que crea subastas) sigue en verde.
