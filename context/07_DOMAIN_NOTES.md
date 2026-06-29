# 07 · Domain Notes

Conceptos, entidades y reglas de negocio **reales** (extraídas del código y del SQL).

> **Fuente de verdad del dominio: [TPO_DAI_1C2026.md](TPO_DAI_1C2026.md)** (consigna oficial del TPO). `frontend-da1/context/consignas.md` es una copia casi idéntica del texto (sin los entregables). Ante cualquier duda sobre "qué debería hacer el sistema", manda el TPO. Este archivo resume lo que el **código** implementa hoy y marca dónde difiere de la consigna.

## Glosario

| Término | Significado |
|---------|-------------|
| **Subasta / remate** | Competencia de ofertas; gana el mayor postor. Modalidad **dinámica ascendente** (los postores ven las ofertas y mejoran la suya). |
| **Precio base** | Valor inicial mínimo de un ítem. |
| **Postor / asistente** | Cliente que participa en una subasta y puede pujar. |
| **Puja (pujo)** | Oferta de dinero sobre un ítem. |
| **Cliente** | Usuario postor registrado y admitido. |
| **Dueño (duenio)** | Persona que consigna artículos. Un cliente se vuelve dueño al consignar. |
| **Artículo** | Bien que un usuario propone consignar (entidad `articulos`). |
| **Producto** | Artículo ya aprobado y convertido en bien subastable (entidad `productos`). |
| **Ítem de catálogo** | Producto incluido en una subasta con precio base y comisión (`itemscatalogo`). |
| **Categoría** | Nivel del usuario/subasta: `comun < especial < plata < oro < platino`. |
| **Multa** | Penalización (10% del valor ofertado) al ganador que no paga. |
| **Consignar** | Proponer un artículo propio para futuras subastas. |

## Entidades principales (resumen; detalle en [11_DATABASE.md](11_DATABASE.md))

`personas` (+`personas_adicionales`) → especializaciones `clientes` (+`clientes_adicionales`), `duenios`, `empleados`, `subastadores`.
`subastas` → `catalogos` → `itemscatalogo` (← `productos`). Participación: `asistentes`, ofertas: `pujos`, ventas: `registrodesubasta`. Pagos: `pagos`, `multas`, `medios_pago`. Consignación: `articulos` → `productos`. Tiempo real: `sesiones_subasta`. Auth: `blacklisted_tokens`.

## Categorías de usuario (orden / peso)

```python
CATEGORIAS_PESO = {"comun": 1, "especial": 2, "plata": 3, "oro": 4, "platino": 5}
```
Para **unirse** a una subasta, el peso del usuario debe ser ≥ peso de la subasta (`subasta_service.join_subasta`).

## Reglas de negocio clave (verificadas en código)

### Registro (2 pasos)
- **Paso 1** (`/auth/registro/paso1`, multipart): datos + foto DNI frente/dorso → sube a Storage → crea persona/cliente pendiente → **e inmediatamente llama `UsuarioRepository.aprobar_registro`** (auto-aprueba) → dispara email con token.
- **Paso 2** (`/auth/registro/paso2`): con el token, setea password; opcionalmente agrega un medio de pago.
- Login exige `estadoRegistro == aprobado`, `admitido == "si"` y `bloqueado == false` (`auth_service.login`).

> ⚠ **El registro hoy se AUTO-APRUEBA.** `registro_paso1` (`app/api/auth.py`) llama a `aprobar_registro` sin pasar por un admin: setea `admitido='si'`, `estado_registro='aprobado'` y genera el token. El endpoint admin `/admin/usuarios/{id}/verificar` (con `aprobar`/`rechazar` + email de éxito/rechazo) **existe pero queda sin efecto** porque el usuario ya entró aprobado. **Trabajo pendiente conocido del equipo: desacoplar el registro** para que un admin evalúe la solicitud antes de habilitar el token. Ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md).

### Unirse a subasta (`POST /subastas/{id}/join`)
Valida en orden (`subasta_service.join_subasta`):
1. Subasta existe y está `abierta`.
2. Categoría suficiente (peso usuario ≥ peso subasta).
3. Usuario no bloqueado / sin multas pendientes (`puede_participar`).
4. Tiene al menos **un medio de pago validado**.
5. No está conectado a otra subasta **en vivo** (sesión activa sobre subasta `abierta` de hoy con hora ya iniciada) → si no, **409**. Las sesiones activas arrastradas de subastas futuras/no-vivas no bloquean la entrada a una sala live.

### Motor de pujas (`subasta_service.procesar_puja`) — REGLA CENTRAL
- Requiere estar unido (asistente) → si no, **403**.
- Ítem se bloquea con `SELECT ... FOR UPDATE` (pessimistic lock).
- Si el ítem ya fue subastado → 400.
- **Subastas NO premium** (categoría ≠ oro/platino):
  - Primera puja: entre `precio_base` y `precio_base + 20%`.
  - Pujas siguientes: entre `mejor_oferta + 1%·base` (mínimo) y `mejor_oferta + 20%·base` (máximo).
- **Subastas premium** (oro/platino): sin tope de 1%/20%; solo debe superar la oferta actual (o ≥ precio base en la primera).
- Tras registrar, devuelve `mejorOfertaActual`, `limiteMinimo`, `limiteMaximo` y hace broadcast SSE.

> El **1% y 20% se calculan sobre el precio base**, no sobre la mejor oferta. Importante para no romper la regla.

### Cierre de subasta (`subasta_service.cerrar_subasta`)
- Por cada ítem con pujas: marca ganador, registra venta en `registrodesubasta`, acumula deuda del cliente (total pujado + comisión) y notifica ("72hs para abonar").
- Ítems **sin pujas**: los adquiere la empresa al precio base; se notifica al dueño.
- Genera un `pago` por cliente ganador y finaliza sesiones.

### Pagos (`/subastas/{id}/pagos`)
- `GET` devuelve el pago pendiente del usuario; `POST` confirma con medio de pago validado, modo de entrega (`envio`/`retiro`) y dirección.
- Si modo = `retiro`, se fuerza `aceptaPerderSeguro = true`.

### Multas y bloqueo (consigna §multa)
Según el TPO: si al pagar el ganador no tiene fondos → **multa del 10% del valor ofertado**, que debe abonar **antes de participar en otra subasta**, y presentar los fondos **dentro de 72hs**; si no cumple, el caso se deriva a la justicia y **pierde acceso a la app**.
- Existen los repos `SubastaRepository.generar_multa` (10% + marca `multa_activa`) y `bloquear_usuario`, **pero NO se invocan desde ningún flujo** (código muerto). La generación automática de la multa/bloqueo está **sin cablear** — ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md).
- Sí funciona el lado consulta/pago: `GET /usuarios/me/multas`, `POST /usuarios/me/multas/pagar`. Al pagar la última multa pendiente se limpia `clientes_adicionales.multa_activa`. El plazo de pago de subastas usa `NOW() + INTERVAL '72 hours'`.

> Actualización 2026-06-21: P0.6 backend cableó este flujo con `POST /admin/pagos/procesar-vencimientos` y validación lazy en join/stream/puja/consulta de pago/listado/pago de multas. Ver [19_P0_6_MULTAS_VENCIMIENTOS_BLOQUEO_NOTES.md](19_P0_6_MULTAS_VENCIMIENTOS_BLOQUEO_NOTES.md).

### Otras reglas de la consigna a tener presentes
- **Asignación de categoría por investigación externa** al registrarse (refuerza que el registro **debería** evaluarse, no auto-aprobarse).
- **La categoría puede mejorar** con la diversidad de medios de pago y la actividad en subastas → **no implementado** (la categoría solo se setea al aprobar).
- **"Streaming" vs tiempo real**: la consigna aclara que el *servicio de streaming* (seguir la subasta en video) **no es parte del desarrollo de la app**. Pero **sí** es requisito que los usuarios conectados reciban las pujas **en tiempo real** para validar/ofertar (eso es el SSE de pujas, en alcance).
- **Garantía / límite de compra**: si el usuario dejó un monto como garantía (ej. cheque certificado), sus compras **no pueden superar ese monto** (`medios_pago.limite_reservado`) → **no se valida** en el código.
- **Subasta colección**: si un cliente entrega muchos artículos, la empresa puede armar una subasta "colección con el nombre del usuario" → **no implementado**.
- **Cuenta receptora del exterior**: el dinero de ventas del consignante va a una cuenta a la vista, posiblemente del exterior, declarada antes (`medios_pago.es_cuenta_receptora`).
- **Catálogos públicos, precio base solo para registrados** (refleja el split `/subastas/publicas` vs autenticado).
- **Una pieza puede tener varios elementos** (ej. "Juego de Té de 18 piezas"): es 1 ítem, no N.

### Consignación: flujo Artículo → Producto (verificado en `articulo_repo` / `articulo_service`)
1. Usuario publica artículo (`POST /articulos`): requiere **≥ 6 fotos**, `esPropietario = true`, `declaraOrigenLicito = true`. Si no, 400. Crea `duenio` si no existía (`ensure_duenio`). Estado inicial `pendiente`.
2. Admin evalúa (`POST /admin/articulos/{id}/evaluar`): `aprobado` (requiere `precioBasePropuesto` y `comisionPropuesta`) o `rechazado` (requiere `motivoRechazo`). Notifica al dueño.
3. Usuario acepta tasación (`POST /articulos/{id}/aceptar-tasacion`, `acepta=true`, requiere estado `aprobado`): crea **póliza de seguro**, crea el **`producto`**, copia fotos a `fotos_adicionales` y deja el artículo trazado.
4. Admin agrega el producto al catálogo de una subasta (`POST /admin/subastas/{id}/catalogo/items`) como `itemscatalogo` (con `precioBase` y `comision`).
5. Seguro: el dueño puede pedir aumento de cobertura (`POST /articulos/{id}/seguro/aumentar`, monto > actual).

## Estados (enums de dominio)

- **Subasta**: `abierta` | `cerrada`.
- **Artículo**: `pendiente` | `en_inspeccion` | `aprobado` | `rechazado` | `devuelto`.
- **Medio de pago / verificación**: `pendiente` | `validado` | `rechazado`.
- **Registro de cliente**: `pendiente` | `aprobado` | `rechazado`.
- **Pago**: `pendiente` | `pagado` | `vencido`.
- **Multa**: `pendiente` | `pagada`.
- **Sesión de subasta**: `activa` | `finalizada`.
- **Notificación (tipo)**: `pago` | `subasta` | `sistema`.
- **Moneda**: `ARS` | `USD` (pujas/respuestas usan `USD` hardcodeado en `procesar_puja`).
