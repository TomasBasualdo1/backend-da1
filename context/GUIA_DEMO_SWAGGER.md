# Guía de demo y payloads Swagger — Sistema de Subastas

> Documento operativo para el día de la demo. Tenerlo abierto al lado de Swagger.
> Verificado contra código real (`app/api/*`, `app/schemas/schemas.py`, `app/services/*`),
> `docs/Swagger_v5.YAML` y el seed `db/seed_subastas_demo.sql`.
> **Nada acá propone implementar features nuevas: es una guía de uso de lo que ya existe.**

---

## 1. Objetivo

Este documento sirve para:

- **presentar el sistema** con un recorrido ordenado y realista;
- **probar endpoints desde Swagger** sin escribir JSONs a mano;
- **evitar trabarse**: tener el orden de los flujos y qué ID copiar en cada paso;
- **saber qué token/ID usar** en cada llamada (público, usuario común, ganador, admin).

No es una auditoría de faltantes (eso está en [26_AUDITORIA_POST_BACKLOG_CONSIGNA.md](26_AUDITORIA_POST_BACKLOG_CONSIGNA.md)). Acá solo se documenta lo que el backend acepta **hoy**.

---

## 2. URLs y setup rápido

| Qué | URL |
|---|---|
| Backend local | `http://127.0.0.1:8000` |
| Swagger local | `http://127.0.0.1:8000/docs` |
| Backend deploy (Render) | `https://backend-da1.onrender.com` |
| Swagger deploy | `https://backend-da1.onrender.com/docs` |

> La URL de Render es la documentada en [18_DEPLOY_RELEASE_HARDENING.md](18_DEPLOY_RELEASE_HARDENING.md). Confirmá que el servicio esté despierto antes de la demo (Render duerme los free tiers; el primer request puede tardar ~30s).

### Cómo autorizar en Swagger

1. Hacé `POST /auth/login` (ver Paso 2) y copiá el `access_token`.
2. Arriba a la derecha en `/docs`, botón **Authorize**.
3. Pegá **solo el token** (Swagger ya antepone `Bearer`). Si el campo pide el esquema completo, usar `Bearer <token>`.
4. A partir de ahí Swagger manda el header `Authorization: Bearer <token>` en todos los endpoints con candado.

### Variables a recordar (sin valores secretos)

Las vas completando a medida que avanzás:

- `<USER_TOKEN>` — token del postor logueado.
- `<ADMIN_TOKEN>` — token del admin (ver advertencia en §3).
- `<SUBASTA_ID>` — id de una subasta abierta (ej. `900001`).
- `<ITEM_ID>` — id de un ítem del catálogo (ej. `900001`).
- `<MEDIO_PAGO_ID>` — id de un medio de pago validado (ej. `900001`).
- `<PAGO_ID>` / `<ARTICULO_ID>` / `<NOTIFICACION_ID>` / `<MULTA_ID>` — según el flujo.

> El header `Idempotency-Key` solo aplica a **pujar** (`POST /subastas/{id}/items/{itemId}/pujar`). Es opcional pero recomendado en la demo.

---

## 3. Usuarios, tokens y datos de demo

El login es por **documento + password** (`POST /auth/login`). Devuelve un `access_token` (JWT, vence a los 30 min por default).

### Usuarios demo del seed (`db/seed_subastas_demo.sql`)

Todos aprobados, admitidos y **con un medio de pago ya validado**. Password común: **`Demo1234!`**.

| Documento | Nombre | usuarioId | Categoría | Medio de pago validado | Moneda | Rol en la demo |
|---|---|---|---|---|---|---|
| `DEMO-POSTOR-1` | Luciana Vega | 900006 | comun | `900001` (tarjeta) | ARS | **Postor común** + **ganador con pago pendiente** (subasta 900006) |
| `DEMO-POSTOR-2` | Tomas Herrera | 900007 | plata | `900002` (cuenta bancaria) | ARS | Postor / ganador con pago **ya pagado** |
| `DEMO-POSTOR-3` | Sofia Nieves | 900008 | oro | `900003` (tarjeta) | USD | Postor categoría **premium** (oro → sin tope 1%/20%) |
| `DEMO-POSTOR-4` | Pedro Alonso | 900009 | platino | `900004` (cheque cert.) | USD | Postor **platino** + cuenta del exterior (UY) |

> **Cómo obtener el token de cada uno:** `POST /auth/login` con `{"documento":"DEMO-POSTOR-1","password":"Demo1234!"}` → copiar `access_token`.

### Admin — ⚠ LEER ANTES DE LA DEMO

El backend define admin **hardcodeado como `usuarioId == 12`** ([dependencies.py:33-38](app/dependencies.py#L33-L38)). El doc de seguridad menciona `1`, pero el código real exige **12**.

- **El seed NO crea ningún usuario con id 12.** Si tu base no tiene un cliente id 12 logueable, **no vas a poder ejecutar ningún endpoint `/admin/*` ni `/subastas/{id}/cerrar`**.
- Para que la demo cubra el lado empresa (aprobar usuarios, verificar medios, evaluar artículos, crear subastas, cerrar), necesitás un usuario **aprobado cuyo `usuarioId` en la DB sea exactamente 12**, con password conocida.
- Cómo verificar/conseguir el admin (decidir antes de la demo):
  - Confirmá si en tu base hay un cliente con `personas.identificador = 12`, `clientes_adicionales.estado_registro='aprobado'`, `clientes.admitido='si'` y password seteada.
  - Si existe, logueate con su documento/password → ese es `<ADMIN_TOKEN>`.
  - Si **no existe**, los pasos admin de esta guía (Paso 9 cierre, Paso 11 multas admin, Paso 13 evaluación, §5.10) **no se podrán correr**. Documentalo como limitación conocida o seedear/promover un id 12 antes (fuera del alcance de este doc).

Placeholders para cuando lo tengas:

- `<DOCUMENTO_ADMIN>` · `<PASSWORD_ADMIN>` · `<ADMIN_TOKEN>`

### Usuario para registro nuevo

No hay un usuario "para registrar" precargado: lo creás en vivo con `POST /auth/registro/paso1` (multipart, ver §5.1). Queda **pendiente** hasta que un admin lo apruebe (necesita el admin id 12). El paso 2 requiere el **token que llega por email**, que no se ve desde Swagger.

### Usuario con multa / bloqueado

El seed **no** trae usuarios con multa activa ni bloqueados (`multa_activa=false`, `bloqueado=false` para todos). El flujo de multas se puede **consultar** (`GET /usuarios/me/multas` devolverá lista vacía) y la generación de multas ocurre vía `POST /admin/pagos/procesar-vencimientos` sobre pagos vencidos. Ver §5.7 y advertencias.

### Dueño / consignador

Cualquier usuario logueado puede consignar (`POST /articulos`); al hacerlo se vuelve "dueño" automáticamente (`ensure_duenio`). Para la demo de consignación se puede usar cualquier `DEMO-POSTOR-*`.

---

## 4. Camino principal recomendado para la demo

Orden pensado para mostrar todo sin trabarse. Para cada paso: endpoint, método, auth, body listo, qué copiar de la respuesta y qué esperar.

> **Nota clave de la demo en vivo:** ya **no hay restricción de antelación** para crear subastas (se eliminó la regla de "≥ hoy+10 días"). Por eso ahora podés crear con `POST /admin/subastas` una subasta con **`fecha` = hoy** (y `hora` ya pasada) para que la app móvil la considere "en vivo" y se pueda pujar **desde la app**. Las subastas del seed siguen siendo futuras, así que para una demo en vivo conviene crear una subasta de hoy. **Desde Swagger** podés pujar sobre cualquier subasta con `estado='abierta'` sin depender de la fecha: el backend permite `join` / `pujar` / `stream` sin chequear la fecha. (Detalle en [27_SUBASTAS_SIN_RESTRICCION_FECHA_NOTES.md](27_SUBASTAS_SIN_RESTRICCION_FECHA_NOTES.md) y [26_AUDITORIA_POST_BACKLOG_CONSIGNA.md](26_AUDITORIA_POST_BACKLOG_CONSIGNA.md) A1.)

### Paso 0 — Healthcheck
- **GET `/`** · sin auth · sin body.
- Esperado: `{"message": "Hello, Snickers!"}`. Confirma que el backend está vivo.

### Paso 1 — Catálogo público
- **GET `/subastas/publicas`** · sin auth · sin body → lista de subastas (sin precio base).
  - Copiar un `id` de subasta abierta, ej. `900001`.
- **GET `/subastas/publicas/{id}`** (ej. `/subastas/publicas/900001`) · sin auth → detalle con catálogo **sin `precioBase`** (los ítems públicos solo muestran `descripcion`, `mejorOfertaActual`, `subastado`, `fotos`).
- Punto de la demo: "el catálogo se ve sin login, pero el precio base no".

### Paso 2 — Login
- **POST `/auth/login`** · sin auth.
```json
{
  "documento": "DEMO-POSTOR-1",
  "password": "Demo1234!"
}
```
- Copiar `access_token` → este es `<USER_TOKEN>`.
- Hacer **Authorize** en Swagger con ese token.

### Paso 3 — Perfil y medios de pago
- **GET `/usuarios/me`** · auth → datos del usuario (incluye `categoria`, `multaActiva`, `bloqueado`).
- **GET `/usuarios/me/medios-pago`** · auth → lista; DEMO-POSTOR-1 ya tiene el medio `900001` validado (`estadoVerificacion: "validado"`).
- (Opcional) **POST `/usuarios/me/medios-pago`** para mostrar alta (ver §5.3). **Queda en `pendiente`** hasta que admin lo verifique.
- (Opcional) **PATCH `/usuarios/me/medios-pago/{id}`** y **DELETE `/usuarios/me/medios-pago/{id}`** para edición/baja.
- Verificación admin del medio: §5.10 (`POST /admin/medios-pago/{id}/verificar`).

### Paso 4 — Subastas autenticadas
- **GET `/subastas`** · auth → listado completo con `categoria`, `estado`, `moneda`.
- **GET `/subastas/{id}`** (ej. `/subastas/900001`) · auth → detalle **con `precioBase`** por ítem **si tu categoría alcanza**. Si tu categoría es menor a la de la subasta, devuelve **403** ("Tu categoria no es suficiente para ver el detalle"). DEMO-POSTOR-1 (comun) puede ver `900001` (comun) pero no `900003` (plata).
- Punto de la demo: comparar el detalle público (sin precio) vs autenticado (con precio).

### Paso 5 — Unirse a una subasta
- **POST `/subastas/{id}/join`** (ej. `/subastas/900001/join`) · auth · **sin body**.
- Validaciones (en orden, [subasta_service.py](app/services/subasta_service.py)): subasta existe y `abierta` → categoría suficiente → no bloqueado/sin multas → **al menos un medio validado** → no estar ya conectado a otra subasta (si no, **409**).
- Esperado: 201. Guardar `<SUBASTA_ID>` = `900001`.
- Tip: usá una subasta cuya categoría matchee al usuario (POSTOR-1 → 900001).

### Paso 6 — Streaming / live (SSE)
- **GET `/subastas/{id}/stream`** · auth (Bearer) · respuesta `text/event-stream`.
- **Swagger NO es cómodo para SSE**: deja la request "colgada" y no renderiza bien el stream. Recomendaciones para la demo:
  - Mostrarlo con `curl` en una terminal aparte:
    ```bash
    curl -N -H "Authorization: Bearer <USER_TOKEN>" \
      http://127.0.0.1:8000/subastas/900001/stream
    ```
  - O explicar que el front se suscribe acá y recibe cada puja en tiempo real.
- Requiere estar **unido** (Paso 5). Si no, devuelve 403 ("Debes unirte a la subasta para recibir actualizaciones en vivo").
- Mientras esté conectado, cada puja nueva emite un evento `data: {...}`; cada 30s manda `: keepalive`.

### Paso 7 — Pujar
- Conseguir el `itemId`: del detalle autenticado (Paso 4), un ítem con `subastado: "no"`. Ej. en subasta `900001`: ítems `900001` y `900002`.
- **POST `/subastas/{id}/items/{item_id}/pujar`** (ej. `/subastas/900001/items/900001/pujar`) · auth.
- Header recomendado:
```txt
Idempotency-Key: demo-puja-001
```
- Body:
```json
{
  "importe": 47500
}
```
- Reglas (subasta **no premium**, categoría ≠ oro/platino):
  - Primera puja: entre `precioBase` y `precioBase + 20%`.
  - Siguientes: entre `mejorOferta + 1%·base` y `mejorOferta + 20%·base`.
  - El 1%/20% se calcula **sobre el precio base**, no sobre la mejor oferta.
  - Ítem `900001`: precioBase 45000 → primera puja válida entre 45000 y 54000.
- Subasta **premium** (oro/platino): sin tope, solo superar la oferta actual (o ≥ base en la primera).
- Copiar de la respuesta: `pujaId`, `mejorOfertaActual`, `limiteMinimo`, `limiteMaximo`, `moneda`, `esGanadoraParcial`.
- (Opcional) puja inválida para mostrar validación: mandar `importe` menor a `limiteMinimo` → 400 con el mensaje del rango.

### Paso 8 — Historial / estado
- **GET `/subastas/{id}/historial`** · auth → lista de pujas del ítem(s). Requiere estar unido (si no, 403).
- La "mejor oferta" se ve en el detalle autenticado (`mejorOfertaActual` por ítem) y en la respuesta de cada puja. No hay endpoint dedicado "mejor oferta".

### Paso 9 — Cierre de subasta (ADMIN)
- **POST `/subastas/{id}/cerrar`** · **token admin (id 12)** · sin body.
- Genera: ganador por ítem, venta en `registrodesubasta`, deuda (pujado + comisión), `pago` por cliente ganador, notificaciones ("72hs para abonar"), finaliza sesiones; ítems sin pujas los "adquiere la empresa" (solo notifica al dueño).
- Esperado: `{"itemsCerrados": N, ...}`.
- ⚠ **Sin admin id 12 no se puede correr.** ⚠ **No cierres una subasta que querés mostrar abierta** para el flujo de pujas. Para demostrar cierre, usá una subasta dedicada.

### Paso 10 — Pagos
- Login como ganador con deuda: **DEMO-POSTOR-1** ya tiene un **pago pendiente** sembrado en la **subasta `900006`** (envío, ARS, total 3.685.000).
- **GET `/subastas/{id}/pagos`** (ej. `/subastas/900006/pagos`) · auth → el pago pendiente del usuario (`totalFinal`, `comision`, `costoEnvio`, `modoEntrega`, `estado`, `fechaLimitePago`).
- **POST `/subastas/{id}/pagos`** · auth → confirma el pago.
  - Modo **envío**:
    ```json
    {
      "medioPagoId": 900001,
      "modoEntrega": "envio",
      "direccionEnvio": "Lavalle 1550, CABA",
      "aceptaPerderSeguro": false
    }
    ```
    Envío exige `direccionEnvio` y suma costo de envío fijo (`COSTO_ENVIO_SUBASTA = 500`).
  - Modo **retiro**:
    ```json
    {
      "medioPagoId": 900001,
      "modoEntrega": "retiro",
      "aceptaPerderSeguro": true
    }
    ```
    Retiro **fuerza** `aceptaPerderSeguro = true` (si mandás false → 400 "Debe aceptar la perdida de seguro para retirar").
- Validaciones: medio pertenece al usuario, está `validado`, moneda compatible, fondos vs `limiteReservado`.
- ⚠ Si querés **mostrar** el pago como pendiente, **no lo confirmes** durante la demo (o usá una subasta de prueba aparte). DEMO-POSTOR-2 tiene un pago ya `pagado` para mostrar el estado final.

### Paso 11 — Multas / bloqueo
- **GET `/usuarios/me/multas`** · auth → lista de multas del usuario (con el seed: **vacía**).
- **POST `/usuarios/me/multas/pagar`** · auth (ver §5.7) → paga una multa puntual.
- Generación de multas / vencimientos (ADMIN): **POST `/admin/pagos/procesar-vencimientos`** · token admin · sin body → procesa pagos vencidos, genera multa del 10% y marca bloqueo según corresponda.
- ⚠ Estado previo necesario: para que esto haga algo, tiene que haber un pago **vencido** (`fechaLimitePago` pasada). El seed pone fechas futuras, así que normalmente no generará multas. No hay endpoint separado de "desbloqueo": el bloqueo se levanta al pagar la multa pendiente.

### Paso 12 — Notificaciones
- **GET `/usuarios/me/notificaciones`** · auth → lista (DEMO-POSTOR-1 tiene 1 no leída tipo `subasta`).
- **POST `/usuarios/me/notificaciones/{id}/leer`** · auth · sin body → marca leída.
- ⚠ Si querés mostrarlas como **no leídas**, no las marques antes.

### Paso 13 — Consignación de artículo
- **POST `/articulos`** · auth · **multipart/form-data** (o JSON con URLs). Requiere **≥ 6 fotos**, `esPropietario=true`, `declaraOrigenLicito=true`. Ver §5.9. Copiar `id` → `<ARTICULO_ID>`. Estado inicial `pendiente`.
- **GET `/articulos/mis-publicaciones`** · auth → mis artículos.
- **GET `/articulos/{id}`** · auth → detalle.
- **POST `/admin/articulos/{id}/evaluar`** · **token admin** → aprobar (con `precioBasePropuesto` + `comisionPropuesta`) o rechazar (con `motivoRechazo`).
- **POST `/articulos/{id}/aceptar-tasacion`** · auth (dueño) · `{"acepta": true}` → si acepta y estado `aprobado`: crea póliza de seguro, crea el **producto** y copia fotos.
- **POST `/articulos/{id}/seguro/aumentar`** · auth · `{"montoNuevo": <mayor al actual>}`.
- **POST `/admin/subastas/{id}/catalogo/items`** · token admin → agrega el producto a una subasta como ítem.

### Paso 14 — Logout
- **POST `/auth/logout`** · auth · sin body → agrega el `jti` del token a la blacklist.
- Esperado: `{"message": "Successfully logged out"}`. Después de esto el token queda **invalidado**: cualquier endpoint autenticado con ese token devuelve 401 ("Token revoked").

---

## 5. Payloads completos por módulo

Catálogo de payloads para copiar a Swagger. Campos cruzados con `app/schemas/schemas.py` y los routers reales.

### 5.1 Auth

**POST `/auth/registro/paso1`** — multipart/form-data · sin auth · status 201. Crea usuario **pendiente** (no auto-aprueba).
```txt
documento: 44999888
nombre: Juan
apellido: Demo
email: juan.demo@example.com
direccion: Av. Demo 123
numeroPais: 1
telefono: 1122334455        (opcional)
fotoFrente: <archivo jpg/png>   (requerido)
fotoDorso: <archivo jpg/png>    (requerido)
```
Esperado: mensaje "La empresa revisará tus datos...". El usuario NO puede loguear hasta que un admin lo apruebe.

**POST `/auth/registro/paso2`** — JSON · sin auth · status 201. El `token` llega por email (no visible en Swagger).
```json
{
  "token": "<TOKEN_DEL_EMAIL>",
  "password": "MiClaveSecreta123",
  "paymentTipo": "tarjeta_credito",
  "paymentDatos": "token-pasarela-demo",
  "paymentMoneda": "ARS",
  "paymentLimite": 500000,
  "paymentPais": "AR"
}
```
> Los campos `payment*` son opcionales. Si no querés cargar medio inicial, mandá solo `token` y `password`.

**POST `/auth/login`** — JSON · sin auth.
```json
{
  "documento": "DEMO-POSTOR-1",
  "password": "Demo1234!"
}
```
Respuesta: `{"access_token": "...", "token_type": "bearer"}`.

**POST `/auth/logout`** — auth · sin body. Invalida el token actual.

**POST `/auth/forgot-password`** — JSON · sin auth.
```json
{ "email": "luciana.demo@example.com" }
```
Siempre responde igual ("si el email existe..."). Envía email con código.

**POST `/auth/reset-password`** — JSON · sin auth.
```json
{
  "token": "<TOKEN_DEL_EMAIL>",
  "newPassword": "NuevaClave123"
}
```

**POST `/auth/verify-email`** — ⚠ **stub sin implementar**. El handler es `pass` (no hace nada, sin body útil). La verificación de email real ocurre vía el token del paso 2. No usar en la demo.

### 5.2 Usuarios / perfil

**GET `/usuarios/me`** — auth · sin body → `Usuario` (incluye `categoria`, `validatedPaymentDiversity`, `multaActiva`, `bloqueado`).

**PATCH `/usuarios/me`** — auth · **multipart/form-data**, todos opcionales:
```txt
nombre: Luciana
apellido: Vega
direccion: Nueva Direccion 456
telefono: 1199998888
foto: <archivo jpg/png>   (opcional)
```

**DELETE `/usuarios/me/foto`** — auth · sin body → borra la foto de perfil.

**GET `/usuarios/me/metricas`** — auth · sin body → `UsuarioMetricas` (subastas participadas/ganadas, % éxito, pujas, montos, etc.).

### 5.3 Medios de pago

**GET `/usuarios/me/medios-pago`** — auth · sin body → lista de `MedioPago`.

**POST `/usuarios/me/medios-pago`** — auth · JSON · status 201. Queda en `pendiente` hasta verificación admin.

Tarjeta de crédito:
```json
{
  "tipo": "tarjeta_credito",
  "datos_encriptados": "token-pasarela-tc-001",
  "moneda": "ARS",
  "limiteReservado": 500000,
  "paisBanco": "AR",
  "esCuentaReceptora": false
}
```
Cuenta bancaria:
```json
{
  "tipo": "cuenta_bancaria",
  "datos_encriptados": "token-pasarela-cb-002",
  "moneda": "ARS",
  "limiteReservado": 900000,
  "paisBanco": "AR",
  "esCuentaReceptora": false
}
```
Cheque certificado (sirve como garantía / límite reservado):
```json
{
  "tipo": "cheque_certificado",
  "datos_encriptados": "token-pasarela-ch-003",
  "moneda": "USD",
  "limiteReservado": 25000,
  "paisBanco": "UY",
  "esCuentaReceptora": true
}
```
> Tipos válidos: `tarjeta_credito`, `cuenta_bancaria`, `cheque_certificado`. Moneda: `ARS` | `USD`. `datos_encriptados` es requerido (token de pasarela; no es la tarjeta real).

**PATCH `/usuarios/me/medios-pago/{id}`** — auth · JSON (solo estos dos campos editables):
```json
{
  "limiteReservado": 700000,
  "esCuentaReceptora": false
}
```

**DELETE `/usuarios/me/medios-pago/{id}`** — auth · sin body · status 204.

**Verificación por admin:** §5.10 (`POST /admin/medios-pago/{id}/verificar`).

### 5.4 Subastas públicas y autenticadas

| Endpoint | Método | Auth | Body | Notas |
|---|---|---|---|---|
| `/subastas/publicas` | GET | No | No | Listado público (sin precio base) |
| `/subastas/publicas/{id}` | GET | No | No | Detalle público; ítems sin `precioBase` |
| `/subastas` | GET | Sí | No | Listado autenticado |
| `/subastas/{id}` | GET | Sí | No | Detalle con `precioBase` si la categoría alcanza; si no, 403 |
| `/subastas/{id}/join` | POST | Sí | No | Unirse (201). Ver validaciones Paso 5 |
| `/subastas/{id}/join` | DELETE | Sí | No | Salir (204) |
| `/subastas/{id}/stream` | GET | Sí | No | SSE; ver Paso 6 |
| `/subastas/{id}/historial` | GET | Sí | No | Historial de pujas (requiere estar unido) |
| `/subastas/{id}/pagos` | GET | Sí | No | Pago pendiente del usuario |
| `/subastas/{id}/pagos` | POST | Sí | JSON | Confirmar pago (§5.6) |
| `/subastas/{id}/cerrar` | POST | **Admin** | No | Cierre (id 12) |

Subastas del seed:

| id | estado | categoría | ítems (subastado=no) |
|---|---|---|---|
| 900001 | abierta | comun | 900001, 900002 |
| 900002 | abierta | especial | 900003, 900004 |
| 900003 | abierta | plata | 900005, 900006 |
| 900004 | abierta | oro (premium) | 900007, 900008 |
| 900005 | abierta | platino (premium) | 900009, 900010 |
| 900006 | cerrada | comun | 900011, 900012 (ya subastados) |

### 5.5 Pujas

**POST `/subastas/{id}/items/{item_id}/pujar`** — auth · status 201.

Header (opcional pero recomendado, evita doble cargo si reintentás):
```txt
Idempotency-Key: demo-puja-001
```
Body:
```json
{
  "importe": 47500
}
```
Respuesta (`PujaResponse`): `pujaId`, `mejorOfertaActual`, `limiteMinimo`, `limiteMaximo`, `moneda`, `esGanadoraParcial`.

Casos de error útiles (opcionales en la demo):
- `importe` menor al `limiteMinimo` → 400 con el rango permitido.
- Pujar sin estar unido → 403 ("Debes unirte a la subasta para poder pujar").
- Ítem ya subastado → 400 ("Este ítem ya fue subastado").
- Reusar el **mismo** `Idempotency-Key` con otro importe mientras está en proceso → 409.

> ⚠ **No reutilices el mismo `Idempotency-Key`** entre pujas distintas: la segunda devuelve el resultado cacheado de la primera (replay), no una puja nueva.

### 5.6 Pagos

**GET `/subastas/{id}/pagos`** — auth · sin body → `Pago` pendiente del usuario (404 si no tiene).

**POST `/subastas/{id}/pagos`** — auth · JSON. Campos (`PagoRequest`): `medioPagoId` (req), `modoEntrega` (`envio`|`retiro`, req), `direccionEnvio` (req si envío), `aceptaPerderSeguro` (forzado true en retiro).

Envío:
```json
{
  "medioPagoId": 900001,
  "modoEntrega": "envio",
  "direccionEnvio": "Lavalle 1550, CABA",
  "aceptaPerderSeguro": false
}
```
Retiro:
```json
{
  "medioPagoId": 900001,
  "modoEntrega": "retiro",
  "aceptaPerderSeguro": true
}
```
- Costo de envío fijo: `500` (`COSTO_ENVIO_SUBASTA`).
- Pago demo pendiente listo: DEMO-POSTOR-1 en subasta `900006`, medio `900001`.

### 5.7 Multas

**GET `/usuarios/me/multas`** — auth · sin body → lista de `Multa` (vacía con el seed).

**POST `/usuarios/me/multas/pagar`** — auth · JSON:
```json
{
  "multaId": 123,
  "medioPagoId": 900001
}
```
Al pagar la última multa pendiente se limpia `multa_activa` (y se levanta el bloqueo asociado).

**POST `/admin/pagos/procesar-vencimientos`** — **token admin** · sin body → procesa pagos vencidos: genera multa del 10% y marca bloqueo. Requiere que existan pagos con `fechaLimitePago` vencida (el seed no los trae).

> No hay endpoint separado de "desbloqueo": se resuelve pagando la multa.

### 5.8 Notificaciones

**GET `/usuarios/me/notificaciones`** — auth · sin body → lista de `Notificacion` (`tipo`: `pago`|`subasta`|`sistema`, `leida`).

**POST `/usuarios/me/notificaciones/{id}/leer`** — auth · sin body → marca leída.

### 5.9 Artículos / consignación

**POST `/articulos`** — auth · status 201. Acepta **multipart/form-data** (recomendado para subir fotos) **o** JSON con URLs.

Multipart:
```txt
descripcion: Reloj antiguo del siglo XIX
historia: Perteneció a una familia... (opcional)
artista: (opcional)
fechaCreacion: 1890-01-01 (opcional, formato date)
esPropietario: true
declaraOrigenLicito: true
fotos: <archivo 1>   ← repetir el campo "fotos" 6 veces o más
fotos: <archivo 2>
fotos: <archivo 3>
fotos: <archivo 4>
fotos: <archivo 5>
fotos: <archivo 6>
documentacionOrigen: <archivo>   (opcional, puede repetirse)
```
JSON alternativo (las fotos deben ser **URLs válidas**, mínimo 6):
```json
{
  "descripcion": "Reloj antiguo del siglo XIX",
  "historia": "Perteneció a una familia...",
  "artista": null,
  "fechaCreacion": "1890-01-01",
  "fotos": [
    "https://example.com/1.jpg",
    "https://example.com/2.jpg",
    "https://example.com/3.jpg",
    "https://example.com/4.jpg",
    "https://example.com/5.jpg",
    "https://example.com/6.jpg"
  ],
  "documentacionOrigen": null,
  "esPropietario": true,
  "declaraOrigenLicito": true
}
```
> ⚠ Menos de 6 fotos, `esPropietario=false` o `declaraOrigenLicito=false` → 400. Copiar el `id` de la respuesta → `<ARTICULO_ID>`.

**GET `/articulos/mis-publicaciones`** — auth · sin body → mis artículos.

**GET `/articulos/{id}`** — auth · sin body → detalle (`estado`, `precioBasePropuesto`, `seguro`, `subastaId`, etc.).

**POST `/articulos/{id}/aceptar-tasacion`** — auth (dueño) · JSON:
```json
{ "acepta": true }
```
Requiere estado `aprobado`. Si `true`: crea seguro + producto.

**POST `/articulos/{id}/seguro/aumentar`** — auth · JSON (monto mayor al actual):
```json
{ "montoNuevo": 950000 }
```

**Evaluación admin:** §5.10 (`POST /admin/articulos/{id}/evaluar`).

### 5.10 Admin

Todos requieren **token admin (usuarioId == 12)**. Sin ese usuario, devuelven 403.

**POST `/admin/usuarios/{id}/verificar`** — JSON. Aprobar:
```json
{ "admitido": true, "categoria": "comun" }
```
Rechazar:
```json
{ "admitido": false, "motivoRechazo": "Documentación inválida" }
```
> Si `admitido=true` falta `categoria` → 400. Si `admitido=false` falta `motivoRechazo` → 400. Envía email al usuario.

**POST `/admin/medios-pago/{id}/verificar`** — JSON:
```json
{ "estadoVerificacion": "validado" }
```
Valores: `validado` | `rechazado`.

**POST `/admin/articulos/{id}/evaluar`** — JSON. Aprobar:
```json
{
  "estado": "aprobado",
  "precioBasePropuesto": 120000,
  "comisionPropuesta": 12000
}
```
Rechazar:
```json
{
  "estado": "rechazado",
  "motivoRechazo": "No cumple requisitos de procedencia"
}
```

**POST `/admin/subastas`** — JSON · status 201. ✅ `fecha` puede ser **cualquier fecha** (incluso hoy): ya no hay restricción de antelación mínima. Para una demo "en vivo" desde la app, usá `fecha` = hoy con una `hora` ya pasada.
```json
{
  "fecha": "2026-08-15",
  "hora": "19:00:00",
  "categoria": "comun",
  "moneda": "ARS",
  "subastadorId": 900002,
  "ubicacion": "Galería Central, CABA",
  "capacidadAsistentes": 80,
  "tieneDeposito": true,
  "seguridadPropia": true
}
```

**POST `/admin/subastas/{id}/catalogo/items`** — JSON · status 201. Mandar **exactamente uno** de `productoId` o `articuloId`.
```json
{
  "productoId": 900001,
  "precioBase": 45000,
  "comision": 4500
}
```
> Si mandás ambos o ninguno → 400. `precioBase` y `comision` deben ser > 0.01.

**Lecturas admin (GET, sin body, token admin):**
- `GET /admin/usuarios/pendientes` — registros pendientes de aprobar.
- `GET /admin/usuarios` — todos los usuarios.
- `GET /admin/articulos/pendientes` — artículos a evaluar.
- `GET /admin/articulos/aprobados-no-catalogados` — productos listos para catálogo.
- `GET /admin/medios-pago/pendientes` — medios a verificar.
- `GET /admin/subastadores` — subastadores disponibles (para `subastadorId` al crear subasta).

**Categorías de usuario (admin):**
- `PATCH /admin/usuarios/{id}/categoria` — JSON `{"categoria": "plata"}` (`comun`|`especial`|`plata`|`oro`|`platino`).
- `POST /admin/usuarios/{id}/recalcular-categoria` — sin body → recalcula y eventualmente sube de categoría (`AutoCategoryResult`).

**Otros admin:**
- `POST /admin/pagos/procesar-vencimientos` — sin body (ver §5.7).
- `POST /subastas/{id}/cerrar` — sin body (está en el router de subastas, pero es admin; ver Paso 9).

### 5.11 Países / uploads / utilitarios

**GET `/paises`** — sin auth · sin body → lista `{numero, nombre, capital}`. Útil para conseguir `numeroPais` (Argentina = 1, Uruguay = 3).

**POST `/uploads/presign`** — sin auth · JSON → genera URL firmada de Supabase Storage para subir un archivo directo.
```json
{
  "filename": "foto.jpg",
  "bucket": "imagenes",
  "content_type": "image/jpeg",
  "expires_in": 3600
}
```
Devuelve `{upload_url, token, public_url, path}`.

**GET `/uploads/fotos/{id}`** — sin auth · sin body → devuelve la imagen binaria (`image/png`) de la tabla `fotos`. Ej: `/uploads/fotos/900001`.

---

## 6. Orden alternativo "seguro" para probar todo antes de la demo

Para ensayar sin ensuciar los datos que querés mostrar en vivo:

1. **GET `/`** — backend vivo.
2. **POST `/auth/login`** admin (id 12, si existe) → `<ADMIN_TOKEN>`.
3. **POST `/auth/login`** DEMO-POSTOR-1 → `<USER_TOKEN>`.
4. **GET `/subastas`** — ver qué subastas abiertas hay.
5. Elegir una subasta **abierta** acorde a la categoría del usuario (POSTOR-1 → 900001).
6. **GET `/subastas/{id}`** — elegir un ítem con `subastado: "no"`.
7. **POST `/subastas/{id}/join`**.
8. **POST `/subastas/{id}/items/{itemId}/pujar`** con `Idempotency-Key` nuevo.
9. **GET `/subastas/{id}/historial`** — confirmar la puja.
10. (Solo si vas a mostrar cierre) cerrar **una subasta de prueba**, no la de la demo.
11. **GET `/subastas/900006/pagos`** con POSTOR-1 — ver pago pendiente (sin confirmar si lo querés mostrar pendiente).
12. **GET `/usuarios/me/notificaciones`** — ver notificaciones.
13. **POST `/articulos`** con 6 fotos — ensayar consignación.

### Advertencias para no romper la demo

- **No cierres** una subasta que necesitás abierta para el flujo de pujas. Usá una aparte para el cierre.
- **No reutilices** el mismo `Idempotency-Key` entre pujas distintas (devuelve replay).
- **No borres** el medio de pago validado del usuario: sin un medio `validado` no podés hacer `join`.
- **No pagues** la deuda que querés mostrar pendiente (POSTOR-1 / subasta 900006). Para mostrar "ya pagado" usá POSTOR-2.
- **No marques** como leídas las notificaciones que querés mostrar como no leídas.
- Ojo con el **token vencido** (30 min): si tarda la demo, volvé a loguear y re-autorizá.
- Tras **logout** el token muere: no sigas usándolo.

### Resetear datos demo

Si necesitás volver al estado inicial del seed:
```bash
psql "$DATABASE_URL" -f db/rollback_seed_subastas_demo.sql
psql "$DATABASE_URL" -f db/seed_subastas_demo.sql
```
> El rollback borra solo los registros demo (IDs 900000+). No toca datos reales ni `paises`.

---

## 7. Checklist de demo

- [ ] Backend levantado (local) o Render despierto (`GET /` responde).
- [ ] Swagger abre (`/docs`).
- [ ] Seed demo cargado (subastas 900001–900006 existen).
- [ ] `<USER_TOKEN>` obtenido (DEMO-POSTOR-1) y **Authorize** hecho.
- [ ] `<ADMIN_TOKEN>` obtenido **o** decidido que el lado admin no se muestra (no hay id 12).
- [ ] Subasta abierta identificada y acorde a la categoría del usuario.
- [ ] Ítem con `subastado: "no"` identificado y su `precioBase` anotado (para pujar en rango).
- [ ] Medio de pago validado identificado (`900001` para POSTOR-1).
- [ ] Pago pendiente preparado si vas a mostrar pagos (POSTOR-1 / subasta 900006).
- [ ] Artículo demo + 6 archivos jpg/png listos si vas a mostrar consignación.
- [ ] `Idempotency-Key` nuevo a mano para cada puja.
- [ ] Rollback/seed a mano por si hay que resetear.

---

## 8. Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---|---|---|
| **401 Unauthorized** | Sin token, token mal pegado o vencido | Re-login y **Authorize** con el token nuevo |
| **401 "Token revoked"** | Hiciste logout con ese token | Login de nuevo |
| **403 admin requerido** | Endpoint `/admin/*` o `/cerrar` sin ser id 12 | Usar `<ADMIN_TOKEN>` (usuarioId 12); si no existe, no se puede |
| **403 "categoria no es suficiente"** | Tu categoría < la de la subasta | Usar un usuario de categoría ≥ (POSTOR-3/4 para premium) |
| **403 "Debes unirte a la subasta"** | Pujar/historial/stream sin `join` previo | Hacer `POST /subastas/{id}/join` primero |
| **403 "Usuario bloqueado o con multas"** | Multa activa o bloqueo | Pagar multa (`/usuarios/me/multas/pagar`) |
| **400 "Debes tener... medio de pago validado"** | Sin medio `validado` | Usar usuario del seed (ya tienen) o que admin valide el medio |
| **404 ID inexistente** | `subastaId`/`itemId`/etc. mal | Releer el ID de la respuesta anterior (no inventarlo) |
| **409 "Ya te encuentras conectado a otra subasta"** | Sesión activa en otra subasta | Salir con `DELETE /subastas/{id}/join` de la otra |
| **400 puja fuera de rango / menor a mejor oferta** | Importe < `limiteMinimo` o > `limiteMaximo` | Usar el rango que devolvió la última respuesta/detalle |
| **400 "Este ítem ya fue subastado"** | Ítem cerrado | Elegir un ítem con `subastado: "no"` |
| **400 "La subasta no está abierta"** / "ya está cerrada" | Subasta cerrada | Usar una abierta (900001–900005) |
| **422 Unprocessable Entity** | Body inválido / falta campo / tipo mal | Revisar el JSON contra §5 (enums exactos, números sin comillas) |
| **400 en multipart** | Falta `fotoFrente`/`fotoDorso` o < 6 fotos en artículo | Adjuntar todos los archivos requeridos |
| **400 pago: "Debe aceptar la perdida de seguro"** | Retiro con `aceptaPerderSeguro=false` | En retiro mandar `true` |
| **Stream no se ve en Swagger** | SSE no renderiza bien en `/docs` | Probarlo con `curl -N` (ver Paso 6) |

---

## 9. Anexo: tabla rápida de endpoints

Leyenda Body: `No` = sin body · `JSON` · `form` = multipart/form-data.

| Método | Ruta | Auth | Body | Rol | ¿Demo? | Observaciones |
|---|---|---|---|---|---|---|
| GET | `/` | No | No | Público | Sí | Healthcheck |
| POST | `/auth/registro/paso1` | No | form | Público | Opc. | DNI frente+dorso; queda pendiente |
| POST | `/auth/registro/paso2` | No | JSON | Público | Opc. | token llega por email |
| POST | `/auth/login` | No | JSON | Público | Sí | documento + password |
| POST | `/auth/logout` | Sí | No | Cualquiera | Sí | invalida el token |
| POST | `/auth/forgot-password` | No | JSON | Público | Opc. | email |
| POST | `/auth/reset-password` | No | JSON | Público | Opc. | token + newPassword |
| POST | `/auth/verify-email` | No | — | — | No | **stub sin implementar** |
| GET | `/usuarios/me` | Sí | No | Usuario | Sí | perfil |
| PATCH | `/usuarios/me` | Sí | form | Usuario | Opc. | campos opcionales |
| DELETE | `/usuarios/me/foto` | Sí | No | Usuario | Opc. | borra foto |
| GET | `/usuarios/me/metricas` | Sí | No | Usuario | Opc. | métricas |
| GET | `/usuarios/me/medios-pago` | Sí | No | Usuario | Sí | listar |
| POST | `/usuarios/me/medios-pago` | Sí | JSON | Usuario | Opc. | queda pendiente |
| PATCH | `/usuarios/me/medios-pago/{id}` | Sí | JSON | Usuario | Opc. | solo límite/cuenta receptora |
| DELETE | `/usuarios/me/medios-pago/{id}` | Sí | No | Usuario | Opc. | 204 |
| GET | `/usuarios/me/multas` | Sí | No | Usuario | Sí | vacía con seed |
| POST | `/usuarios/me/multas/pagar` | Sí | JSON | Usuario | Opc. | multaId + medioPagoId |
| GET | `/usuarios/me/notificaciones` | Sí | No | Usuario | Sí | listar |
| POST | `/usuarios/me/notificaciones/{id}/leer` | Sí | No | Usuario | Sí | marcar leída |
| GET | `/subastas/publicas` | No | No | Público | Sí | sin precio base |
| GET | `/subastas/publicas/{id}` | No | No | Público | Sí | detalle público |
| GET | `/subastas` | Sí | No | Usuario | Sí | listado |
| GET | `/subastas/{id}` | Sí | No | Usuario | Sí | con precio base si categoría alcanza |
| POST | `/subastas/{id}/join` | Sí | No | Usuario | Sí | unirse (201) |
| DELETE | `/subastas/{id}/join` | Sí | No | Usuario | Opc. | salir (204) |
| GET | `/subastas/{id}/stream` | Sí | No | Usuario | Sí | SSE; mejor por curl |
| POST | `/subastas/{id}/items/{item_id}/pujar` | Sí | JSON | Usuario | Sí | header `Idempotency-Key` |
| GET | `/subastas/{id}/historial` | Sí | No | Usuario | Sí | requiere join |
| GET | `/subastas/{id}/pagos` | Sí | No | Usuario | Sí | pago pendiente |
| POST | `/subastas/{id}/pagos` | Sí | JSON | Usuario | Sí | envío/retiro |
| POST | `/subastas/{id}/cerrar` | Sí | No | **Admin** | Sí | id 12 |
| POST | `/articulos` | Sí | form/JSON | Usuario | Sí | ≥6 fotos |
| GET | `/articulos/mis-publicaciones` | Sí | No | Usuario | Sí | mis artículos |
| GET | `/articulos/{id}` | Sí | No | Usuario | Sí | detalle |
| POST | `/articulos/{id}/aceptar-tasacion` | Sí | JSON | Dueño | Sí | acepta:true |
| POST | `/articulos/{id}/seguro/aumentar` | Sí | JSON | Dueño | Opc. | montoNuevo |
| POST | `/admin/usuarios/{id}/verificar` | Sí | JSON | **Admin** | Sí | aprobar/rechazar |
| POST | `/admin/medios-pago/{id}/verificar` | Sí | JSON | **Admin** | Opc. | validado/rechazado |
| POST | `/admin/articulos/{id}/evaluar` | Sí | JSON | **Admin** | Sí | aprobado/rechazado |
| POST | `/admin/subastas` | Sí | JSON | **Admin** | Opc. | fecha > hoy+10d |
| POST | `/admin/subastas/{id}/catalogo/items` | Sí | JSON | **Admin** | Opc. | uno de producto/articulo |
| POST | `/admin/pagos/procesar-vencimientos` | Sí | No | **Admin** | Opc. | genera multas/bloqueo |
| GET | `/admin/usuarios/pendientes` | Sí | No | **Admin** | Opc. | — |
| GET | `/admin/usuarios` | Sí | No | **Admin** | Opc. | — |
| PATCH | `/admin/usuarios/{id}/categoria` | Sí | JSON | **Admin** | Opc. | set categoría |
| POST | `/admin/usuarios/{id}/recalcular-categoria` | Sí | No | **Admin** | Opc. | auto upgrade |
| GET | `/admin/articulos/pendientes` | Sí | No | **Admin** | Opc. | — |
| GET | `/admin/articulos/aprobados-no-catalogados` | Sí | No | **Admin** | Opc. | — |
| GET | `/admin/medios-pago/pendientes` | Sí | No | **Admin** | Opc. | — |
| GET | `/admin/subastadores` | Sí | No | **Admin** | Opc. | para subastadorId |
| GET | `/paises` | No | No | Público | Opc. | numeroPais |
| POST | `/uploads/presign` | No | JSON | Público | Opc. | URL firmada Storage |
| GET | `/uploads/fotos/{id}` | No | No | Público | Opc. | imagen binaria |

---

### Notas finales de honestidad operativa

- **Admin id 12**: el mayor riesgo de la demo. Sin un usuario logueable con `usuarioId == 12`, todos los flujos `/admin/*` y `/cerrar` quedan inaccesibles. Confirmar antes.
- **SSE en Swagger**: incómodo; usar `curl -N`.
- **Subastas siempre futuras**: la app móvil no llega a la sala en vivo, pero **desde Swagger sí** se puede `join`+`pujar` sobre cualquier subasta `abierta`.
- **`verify-email`**: stub vacío, no usar.
- **Multas**: el seed no trae multas ni pagos vencidos, así que `procesar-vencimientos` no generará nada salvo que prepares un pago vencido en la DB.
</content>
</invoke>
