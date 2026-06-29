# 29 · El usuario puede elegir moneda (ARS/USD) al consignar un artículo

**Fecha del cambio:** 2026-06-28

## Qué se cambió

Se agregó un selector de moneda (ARS / USD) al formulario de consignación de artículos para que el usuario elija en qué divisa declara su valor estimado. Antes, el formulario mostraba un label fijo "Valor Estimado (USD) *" sin permitir elegir la moneda, y el dato no se persistía como campo de moneda en la base de datos.

Ahora el usuario ve dos botones (USD / ARS) junto al campo numérico, elige una moneda, y ese dato viaja al backend y se guarda en la columna `moneda` de la tabla `articulos`. En la vista de inspección del admin, el detalle del artículo muestra la moneda elegida por el usuario junto al valor estimado.

## Por qué

La consigna del TPO pide soporte multimoneda real (`ARS` / `USD`) en todo el sistema. Las subastas ya tenían columna `moneda` (ver [24_P2_3_MONEDA_SUBASTA_NOTES.md](24_P2_3_MONEDA_SUBASTA_NOTES.md)), los medios de pago también, pero el artículo consignado seguía sin registrar la moneda del valor estimado. El formulario de consignación solo mostraba "USD" de forma rígida, contradiciendo la arquitectura multimoneda del resto del sistema. El usuario debía poder expresar su estimación en la moneda que corresponda, aunque luego el admin asigne el precio base definitivo con su propia moneda durante la evaluación.

## Dónde se cambió (10 archivos)

| Capa | Archivo | Cambio |
|------|---------|--------|
| **DB** — migración | [db/migration_p2_4_add_moneda_articulos.sql](../db/migration_p2_4_add_moneda_articulos.sql) | `ALTER TABLE articulos ADD COLUMN IF NOT EXISTS moneda character varying` |
| **DB** — snapshot DDL | [db/Estructura-PostgreSQL-da1-updated.sql](../db/Estructura-PostgreSQL-da1-updated.sql) | Agrega `moneda character varying` a la definición de `articulos` |
| **Backend** — schema | [app/schemas/schemas.py](../app/schemas/schemas.py) `ArticuloInput` | Campo `moneda: Optional[Moneda]` |
| **Backend** — schema | [app/schemas/schemas.py](../app/schemas/schemas.py) `Articulo` | Campo `moneda: Optional[str]` |
| **Backend** — API | [app/api/articulos.py](../app/api/articulos.py) `_build_articulo_input` | Lee `moneda` del form multipart |
| **Backend** — repositorio | [app/repositories/articulo_repo.py](../app/repositories/articulo_repo.py) | `_row_to_articulo`: convierte el campo a `str`. `create_articulo`: INSERT incluye la columna `moneda`. `get_articulo`, `list_articulos_by_owner`, `get_all_pendientes`: SELECT agregan `a.moneda` |
| **Frontend** — tipos | [frontend-da1/src/types/article.ts](../../frontend-da1/src/types/article.ts) | `ArticuloInput` recibe `moneda?: Moneda`; `Articulo` recibe `moneda?: string` |
| **Frontend** — servicios | [frontend-da1/src/services/articleService.ts](../../frontend-da1/src/services/articleService.ts) | `normalizeArticulo` mapea el campo; `publicar` lo agrega al `FormData` |
| **Frontend** — servicios | [frontend-da1/src/services/adminService.ts](../../frontend-da1/src/services/adminService.ts) | `normalizeArticulo` mapea el campo `moneda` |
| **Frontend** — consignar | [frontend-da1/app/consignar.tsx](../../frontend-da1/app/consignar.tsx) | Nuevo estado `moneda` (default `"USD"`). Selector de dos botones USD/ARS con estilo toggle. El `handleSubmit` pasa `moneda` en la llamada a `articleService.publicar()`. Label cambiado de `"Valor Estimado (USD) *"` a `"Valor Estimado *"`. |
| **Frontend** — admin | [frontend-da1/app/admin/articles.tsx](../../frontend-da1/app/admin/articles.tsx) | Detail modal: "Valor Est. Usuario" ahora muestra `{moneda} X,XXX.XX` usando la moneda real del artículo en lugar de hardcodear `USD`. |

> ⚠ **Acción de deploy requerida:** correr `db/migration_p2_4_add_moneda_articulos.sql` en Supabase/PostgreSQL. La columna es nullable y los registros existentes quedan con `NULL`. La migración es idempotente.

## Impacto en la demo

- Al consignar un artículo desde la app, el usuario ve dos botones para elegir **USD** o **ARS** junto al campo de valor estimado. El botón activo queda resaltado en color oscuro.
- El ícono de moneda (`US$` / `$`) cambia dinámicamente según la selección.
- El dato de moneda se persiste en la BD y se muestra en la vista de inspección del admin ("Ficha Técnica") junto al valor estimado.
- Por defecto, la moneda seleccionada es `USD` para mantener retrocompatibilidad con el comportamiento anterior.

## Convivencia con otros campos de moneda

- `articulos.moneda`: la elige el **usuario** al consignar para su `precio_sugerido_usuario`. Es una referencia; el admin puede ignorarla al evaluar.
- `subastas.moneda`: la define el **admin** al crear la subasta (ver [24_P2_3_MONEDA_SUBASTA_NOTES.md](24_P2_3_MONEDA_SUBASTA_NOTES.md)). Es la moneda oficial en la que operan pujas, garantías y pagos de esa subasta.
- `medios_pago.moneda`: la elige el **usuario** al registrar un medio de pago. Es la moneda en que opera ese medio.
- Son campos independientes; la moneda del artículo no condiciona la moneda de la subasta donde se catalogue, ni viceversa. El admin decide la moneda final al momento de crear la subasta y tasar el artículo.

## Tests

La suite completa de 150 tests del backend pasa sin modificaciones (150 OK, 1 skipped). Los tests existentes que verifican creación y consulta de artículos (`test_flow_articulo_producto`) no validaban la ausencia del campo `moneda`, por lo que la nueva columna nullable no los rompe. El test que valida el flujo de evaluación admin sigue pasando.
