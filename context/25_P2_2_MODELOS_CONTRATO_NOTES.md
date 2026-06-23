# P2.2 - Corregir modelos generados y nombres inconsistentes

## Objetivo
Resolver inconsistencias de contrato, modelos y nombres generados entre el Swagger, los esquemas de Pydantic y los tipos del Frontend, eliminando los nombres genéricos como `Estado1` o `Tipo2` y asegurando que las serializaciones y la lógica respeten el contrato de datos.

## Estado inicial verificado
- Se comprobó el estado de Git en ambos repositorios.
- Se verificó que la suite de pruebas del backend tuviera 110 tests pasando como línea base antes de iniciar las modificaciones.

## Preparación Git
- Se crearon y cambiaron las ramas locales en ambos repositorios a `feature/p2-2-modelos-contrato`:
  - En Backend basada en `main`.
  - En Frontend basada en `master`.

## Relación con P2.3
### P2.3 detectado
P2.3 ("Definir moneda real de subasta") ya está implementado e integrado en la rama `main` del backend. Agregó la columna `moneda` a la tabla `subastas` y adaptó la lógica de pujas, garantías y pagos para usarla dinámicamente en lugar de asumir siempre `"USD"`.

### Archivos compartidos con P2.3
- `app/repositories/subasta_repo.py`
- `app/services/subasta_service.py`
- `db/Estructura-PostgreSQL-da1-updated.sql`
- Varios archivos de pruebas unitarias.

### Cómo se preservó moneda
- Se mantuvo intacto el enum `Moneda` (`ARS` | `USD`) en `schemas.py`.
- No se revirtió a hardcodear `"USD"` en los listados, detalles, pujas ni pagos.
- Se corrigió únicamente la descripción obsoleta en `docs/Swagger_v5.YAML` para `SubastaListado.moneda` que decía que el backend siempre responde `"USD"` por falta de columna.
- Los nuevos tests agregados validan explícitamente que los listados y detalles devuelvan la moneda real guardada en la base de datos.

## Inventario de inconsistencias
| Archivo | Modelo / enum / campo | Problema | Decisión |
|---|---|---|---|
| `docs/Swagger_v5.YAML` | `SubastaListado.moneda` | Descripción y default obsoletos indicando USD hardcodeado. | Modificar descripción para reflejar que es dinámico. Quitar default. |
| `schemas.py` | `EstadoVerificacion1` | Nombre genérico autogenerado para el estado de verificación. | Renombrar a `EstadoVerificacionMedioPagoInput`. |
| `schemas.py` | `Estado` | Nombre genérico autogenerado para el estado de la multa. | Renombrar a `EstadoMulta`. |
| `schemas.py` | `Tipo2` | Nombre genérico autogenerado para el tipo de notificación. | Renombrar a `TipoNotificacion`. |
| `schemas.py` | `Estado1` | Nombre genérico autogenerado para el estado de la subasta. | Renombrar a `EstadoSubasta`. |
| `schemas.py` | `Estado2` | Nombre genérico autogenerado para el estado del pago. | Renombrar a `EstadoPago`. |
| `schemas.py` | `Estado3` | Nombre genérico autogenerado para el estado de la sesión de subasta. | Renombrar a `EstadoSesionSubasta`. |
| `schemas.py` | `Type` | Nombre genérico autogenerado para el tipo de evento SSE (`StreamEvent`). Además, faltaba el valor `'cierre'`. | Renombrar a `TipoStreamEvent` y añadir el miembro `cierre`. |
| `schemas.py` | `Estado4` | Nombre genérico autogenerado para el estado del artículo. | Renombrar a `EstadoArticulo`. |
| `schemas.py` | `Estado5` | Nombre genérico autogenerado para el estado de evaluación de tasación. | Renombrar a `EstadoEvaluacionArticulo`. |

## Decisiones de contrato
### subastado
- **Decisión**: Se mantiene como string enum `"si"` | `"no"`.
- **Compatibilidad**: Coincide con la restricción `CHECK` de la base de datos, el Swagger y las definiciones de TypeScript. El normalizador del frontend continúa aceptando valores viejos (como booleanos) defensivamente.

### estado
- **Decisión**: Se renombraron los enums genéricos a variantes específicas y claras: `EstadoMulta`, `EstadoSubasta`, `EstadoPago`, `EstadoSesionSubasta`, `EstadoArticulo`, `EstadoEvaluacionArticulo`, `EstadoVerificacionMedioPagoInput`. Los valores textuales subyacentes permanecieron iguales para preservar la lógica de negocio y la base de datos.

### tipo
- **Decisión**: Se renombró `Tipo2` a `TipoNotificacion` y `Type` a `TipoStreamEvent`. En `TipoStreamEvent` se agregó el valor `'cierre'` para alinear el contrato con el evento SSE emitido al cerrar subastas, soportado de forma nativa por el frontend.

### moneda
- **Decisión**: Se preserva el contrato multimoneda (`ARS` / `USD`). Se eliminaron las notas explicativas obsoletas en Swagger, confirmando que la moneda real de la subasta se lee de la DB.

## Estrategia de modelos
### Regeneración / edición manual / híbrida
Se adoptó una estrategia híbrida controlada mediante edición manual. Dado que no existen scripts versionados de codegen ni dependencias específicas del generador instaladas, la regeneración automática corría el riesgo de alterar código de P2.3 o producir un diff masivo innecesario. 

### Comandos usados o motivo por el que no se usaron
No se utilizó `datamodel-codegen` debido a la falta de configuración específica y entorno preestablecido para dicho fin. La edición manual quirúrgica en `schemas.py` y `__init__.py` garantizó seguridad, robustez y un blast radius mínimo.

## Qué se implementó
### Backend
- Modificación de `app/schemas/schemas.py` para renombrar los 9 enums genéricos y ajustar las referencias en todos los modelos Pydantic.
- Modificación de `app/schemas/__init__.py` para actualizar las importaciones y exportaciones.

### Frontend
- Sincronización de `context/Swagger_v5.YAML` desde el backend.
- Corrección de un error sintáctico preexistente de claves duplicadas (`cancelBtn`/`cancelBtnText`) en `app/(tabs)/profile.tsx` para permitir que el linter del frontend compile limpiamente.

### Swagger
- Refactorización de inline enums en `docs/Swagger_v5.YAML` (Backend) hacia definiciones explícitas en `components/schemas` con nombres semánticos.
- Corrección del campo `moneda` obsoleta en `SubastaListado`.

### Tests
- Creación de `tests/test_modelos_contrato.py` que:
  - Valida la carga correcta de las importaciones de enums.
  - Verifica que los enums acepten los valores válidos de base de datos.
  - Valida la serialización de `subastado: "no"` en el detalle público.
  - Valida la serialización del detalle autenticado con artículos vendidos y no vendidos.
  - Valida el flujo multimoneda en listados público y autenticado.
  - Valida la aceptación de eventos de tipo `cierre` en el stream de eventos.

## Archivos modificados
- `backend-da1/docs/Swagger_v5.YAML`
- `backend-da1/app/schemas/schemas.py`
- `backend-da1/app/schemas/__init__.py`
- `backend-da1/tests/test_modelos_contrato.py`
- `frontend-da1/context/Swagger_v5.YAML`
- `frontend-da1/app/(tabs)/profile.tsx`

## Comandos ejecutados
- Checkout de ramas seguras:
  - `git checkout -b feature/p2-2-modelos-contrato` en ambos repos.
- Pruebas unitarias backend:
  - `.venv/bin/python -m unittest tests.test_modelos_contrato -v`
  - `.venv/bin/python -m unittest discover -s tests -v`
- Verificación sintáctica:
  - `.venv/bin/python -m py_compile app/schemas/schemas.py app/api/subastas.py app/services/subasta_service.py app/repositories/subasta_repo.py`
- Linter frontend:
  - `npm run lint`

## Resultados
- **Backend tests**: 116 tests pasados (115 exitosos, 1 skipped).
- **Linter frontend**: 0 errores, 21 warnings de código inactivo/común.
- **Chequeo de sintaxis**: Éxito total.

## Riesgos / pendientes
- Ninguno detectado. El cambio mantiene una alta retrocompatibilidad y alinea de manera estricta el contrato entre las aplicaciones.
