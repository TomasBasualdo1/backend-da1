# 28 · Admin puede ver el precio sugerido por el usuario al consignar un artículo

**Fecha del cambio:** 2026-06-28

## Qué se cambió

Se agregó una columna `precio_sugerido_usuario` a la tabla `articulos` para que el usuario que consigna un artículo pueda declarar un valor estimado, y que el administrador (id 12) pueda ver ese valor al inspeccionar el artículo pendiente.

Antes, la app frontend (`consignar.tsx`) ya pedía un "Valor Estimado (USD)" al usuario en el paso 2 del formulario, pero ese dato **nunca se enviaba al backend ni se persistía**. El admin al auditar artículos pendientes no veía ninguna referencia de precio.

## Por qué

La consigna del TPO pide que el administrador evalúe los artículos y proponga un precio base + comisión (`precio_base_propuesto` / `comision_propuesta`). Para tomar una decisión informada, el admin necesita saber cuánto cree el usuario que vale el artículo. Este faltante fue identificado como parte del flujo de consignación en la auditoría post-backlog.

## Dónde se cambió (9 archivos)

| Capa | Archivo | Cambio |
|------|---------|--------|
| **DB** — migración | [db/migration_p0_4_add_precio_sugerido_usuario.sql](../db/migration_p0_4_add_precio_sugerido_usuario.sql) | `ALTER TABLE articulos ADD COLUMN IF NOT EXISTS precio_sugerido_usuario numeric` |
| **Backend** — schema | [app/schemas/schemas.py](../app/schemas/schemas.py) `ArticuloInput` (L390) | Campo `precioSugeridoUsuario: Optional[float]` |
| **Backend** — schema | [app/schemas/schemas.py](../app/schemas/schemas.py) `Articulo` (L467) | Campo `precioSugeridoUsuario: Optional[float]` |
| **Backend** — API | [app/api/articulos.py](../app/api/articulos.py) `_build_articulo_input` (L83) | Lee `precioSugeridoUsuario` del form multipart |
| **Backend** — repositorio | [app/repositories/articulo_repo.py](../app/repositories/articulo_repo.py) | `_row_to_articulo`: convierte el campo a `float`. `create_articulo`: INSERT incluye la columna. `get_articulo`, `list_articulos_by_owner`, `get_all_pendientes`: SELECT agregan `a.precio_sugerido_usuario AS "precioSugeridoUsuario"` |
| **Frontend** — tipos | [frontend-da1/src/types/article.ts](../../frontend-da1/src/types/article.ts) | `ArticuloInput` y `Articulo` reciben `precioSugeridoUsuario?: number` |
| **Frontend** — servicios | [frontend-da1/src/services/articleService.ts](../../frontend-da1/src/services/articleService.ts) | `normalizeArticulo` mapea el campo; `publicar` lo agrega al `FormData` |
| **Frontend** — servicios | [frontend-da1/src/services/adminService.ts](../../frontend-da1/src/services/adminService.ts) | `normalizeArticulo` mapea el campo |
| **Frontend** — consignar | [frontend-da1/app/consignar.tsx](../../frontend-da1/app/consignar.tsx) `handleSubmit` (L123) | Pasa `precioSugeridoUsuario: parseFloat(valorEstimado)` en la llamada a `articleService.publicar()` |
| **Frontend** — admin | [frontend-da1/app/admin/articles.tsx](../../frontend-da1/app/admin/articles.tsx) | Detail modal: nueva fila "Valor Est. Usuario" en la Ficha Técnica, muestra `USD X,XXX.XX` o "No declarado" |

> ⚠ **Acción de deploy requerida:** correr `db/migration_p0_4_add_precio_sugerido_usuario.sql` en Supabase/PostgreSQL. La columna es nullable y los registros existentes quedan con `NULL`. La migración es idempotente (`ADD COLUMN IF NOT EXISTS`).

## Impacto en la demo

- Al consignar un artículo desde la app, el usuario completa "Valor Estimado (USD)" y ese dato se persiste en la BD.
- El admin, en la pantalla **Inspección de Artículos**, al abrir el detalle de un artículo pendiente ve el valor estimado declarado por el usuario en la sección "Ficha Técnica", ayudando a decidir el `precioBasePropuesto` que fijará al evaluar.

## Convivencia con `precio_base_propuesto`

- `precio_sugerido_usuario`: lo declara el **usuario** al consignar (referencia, puede ser `NULL`).
- `precio_base_propuesto`: lo asigna el **admin** durante la evaluación (hasta entonces es `NULL`).
- Son columnas independientes; el admin puede contrastar ambos valores en la misma vista.

## Tests

No existían tests previos para el flujo de consignación de artículos, por lo que no se rompió ninguno. Los tests existentes (`test_articulos`, `test_admin`) que verifican creación/consulta de artículos deben seguir pasando porque la nueva columna es nullable y los tests no validaban la ausencia del campo.
