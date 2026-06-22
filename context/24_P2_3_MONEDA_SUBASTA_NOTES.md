# P2.3 - Definir Moneda Real de Subasta

## Propósito
El objetivo de este ticket fue dejar de asumir que todas las subastas operan en `"USD"` de forma rígida (hardcodeada) y en su lugar, almacenar y leer la moneda de cada subasta directamente desde la base de datos. Esto permite el soporte para subastas en múltiples divisas de manera dinámica.

## Cambios Realizados

### 1. Base de Datos
- **Script:** `db/Estructura-PostgreSQL-da1-updated.sql`
- **Modificación:** Se agregó la columna `moneda VARCHAR(3) NOT NULL DEFAULT 'USD'` a la tabla `subastas`.
- **Justificación:** Permitir que cada subasta tenga su propia divisa guardada en el schema, manteniendo retrocompatibilidad mediante el default constraint para las filas ya existentes.

### 2. Capa de Repositorio (Repos)
- **Archivo:** `app/repositories/subasta_repo.py`
- **Modificación:** 
  - Se eliminó la constante global `DEFAULT_SUBASTA_MONEDA = "USD"`.
  - El método `crear_subasta` ahora inserta el valor de la moneda elegido (extraído de `subasta.moneda.value`).
  - Las consultas `get_publicas`, `get_todas`, `get_publica_detalle`, `get_detalle`, entre otras, fueron actualizadas para hacer `SELECT ... s.moneda` en lugar de proyectar `'USD' AS moneda`.
  - Los métodos `get_garantia_validada_for_update` y `get_exposicion_pagos_pendientes` ahora aceptan la moneda de forma dinámica por parámetro en vez del argumento por default.
  - `get_subasta_basica` fue actualizado para incluir `moneda` en su `SELECT`, ya que el servicio lo necesita para propagar la moneda real.
  - La query del historial de pujas (`get_historial_pujas` / endpoint de pujas por subasta) ahora hace `JOIN subastas s ON a.subasta = s.identificador` para obtener `s.moneda` en lugar de proyectar `'USD' AS moneda`.

### 3. Capa de Servicios
- **Archivo:** `app/services/subasta_service.py`
- **Modificación:**
  - En `procesar_puja`, antes de validar la garantía y la exposición de pagos pendientes, se extrae de la base de datos la moneda oficial de la subasta con `get_subasta_basica` y se usa en las delegaciones a repositorio. La moneda de retorno en la respuesta de la puja respeta la moneda real obtenida de la Base de Datos.
  - Al ejecutar `cerrar_subasta`, se propaga la moneda oficial registrada en la subasta hacia la capa de repositorio al momento de llamar a `generar_pago`.

### 4. Tests Unitarios
- **Archivos Modificados:** `test_garantia_limite.py`, `test_subasta_listados_detalles.py`, `test_puja_idempotency.py`, `test_subasta_multas.py`, `test_subasta_pagos.py`, `test_subasta_stream.py`.
- **Modificación:** Dado que ahora dependemos del dato de `moneda` obtenido desde la DB (específicamente a través del método `get_subasta_basica`), todos los tests que aplicaban un *mock* (`unittest.mock.patch`) a `get_subasta_basica` debieron ser actualizados para agregar `{"moneda": "USD"}` al valor de retorno fingido (`return_value`). De esta forma, aseguramos la estabilidad del entorno de pruebas. También se ajustaron los asserts sobre las consultas SQL que ya no pasan `"USD"` como argumento sino que extraen la columna.

## Consideraciones a Futuro
- Si el frontend permite crear nuevas subastas mediante la API, se debe enviar explícitamente el campo `moneda` que soporte la aplicación (con validación de Enum).
- Todos los componentes financieros (Pagos, Limite de Garantía, etc) ya comparan per-moneda, por lo que el sistema base es multi-divisa. La capa de cliente de pago a nivel externo (Pasarela) deberá tener su propio switch de divisa basado en este dato.
