# Auditoría post-backlog contra consigna TPO

> Fecha: 2026-06-27 · Rama backend: `feature/p2-2-modelos-contrato` · Auditor: revisión técnico-funcional sobre código real.
> **No se modificó código.** Este documento es solo el informe de faltantes.

## 1. Resumen ejecutivo

La app **cumple lo importante de la consigna en su mayoría**: el backlog `14_*` quedó desactualizado en sentido optimista — casi todos sus P0/P1 ya están implementados y verificados en código (registro desacoplado, guard admin en todos los endpoints, idempotencia de pujas, SSE end-to-end con fallback a polling, multas/vencimientos/bloqueo, garantía/límite reservado, pago de subasta con validaciones, mejora automática de categoría, moneda real por subasta, UI admin, UI de pago, seguimiento de consignación). El front apunta al backend online (`https://backend-da1.onrender.com`).

Pero quedan **faltantes que sí afectan la demo final y el cumplimiento end-to-end**, sobre todo de integración y datos:

1. **(P0) El circuito en vivo es inalcanzable desde la app con datos normales.** Toda entrada a la sala (lobby `live`, detalle, tab subastas) se gatea por `isAuctionLive`, que exige `fecha == hoy` y hora ya pasada; pero el `CHECK` de `subastas.fecha` y `create_subasta` obligan a fechas ≥ hoy+10 días. Ninguna subasta puede estar "en vivo" → el corazón del TPO (puja dinámica ascendente + tiempo real) no se puede mostrar sin tocar la DB a mano.
2. **(P0) No existe un admin usable.** El admin está hardcodeado a `usuarioId == 12` (back y front), pero el seed no crea ningún cliente con id 12, y los empleados no tienen credenciales (no loguean). Sin admin no se demuestra: aprobar registros, verificar medios de pago, evaluar artículos, crear subastas/catálogo, cerrar subasta. Y como el registro ya **no** se auto-aprueba, los nuevos usuarios quedan pendientes para siempre.
3. **(P1) Cierre solo manual + sin coherencia temporal.** No hay scheduler; el cierre depende de admin (ver punto 2). Con subastas siempre futuras y sin apertura/cierre por horario, el ciclo "abre → puja → cierra → pago" no fluye solo.
4. **(P1/P2) "Empresa compra al precio base si nadie puja"** solo notifica al dueño: no registra venta, no cambia dueño ni paga al consignante.
5. **(P2) Pago al consignante / cuenta receptora del exterior:** el campo existe pero no hay flujo donde el dueño cobre lo vendido.

**Atacar primero:** el seed/datos de demo y el admin (faltante 2) y la jugabilidad del live (faltante 1). Son baratos (datos + 1 ajuste de gating/seed) y desbloquean toda la demostración. Sin ellos, la entrega "parece completa" pero no se puede recorrer en vivo.

## 2. Metodología

- **Fuente de verdad:** `context/TPO_DAI_1C2026.md` (consigna oficial).
- **Estado real:** se leyó código, no documentación. Backend: `app/api/{auth,admin,subastas}.py`, `app/dependencies.py`, `app/services/{subasta_service,category_service}.py`, `db/Estructura-PostgreSQL-da1-updated.sql`, `db/seed_subastas_demo.sql`. Frontend: `app/(tabs)/{live,profile}.tsx`, `app/subasta/[id]/index.tsx`, `app/pagos/[subastaId].tsx`, `app/admin/*`, `src/services/{auctionService,articleService}.ts`, `src/utils/auctionSchedule.ts`, `src/context/AuthContext.tsx`, `.env`.
- **Contexto:** `00,07,08,14,15` y notas `16–25`. Se trató el backlog `14_*` como **no** fuente de verdad (estaba desactualizado: muchos P0/P1 figuran "Parcial/Pendiente" pero el código ya los resuelve).
- **No se ejecutó nada ni se modificó código.** Hallazgos por lectura cruzada consigna ↔ código ↔ datos de demo.

## 3. Tabla de faltantes importantes

| ID | Prio | Flujo | Qué pide la consigna | Qué hace hoy la app | Estado | Impacto | Backend | Frontend | DB/Swagger | Recomendación |
|----|------|-------|----------------------|---------------------|--------|---------|---------|----------|------------|---------------|
| A1 | P0 | Subasta en vivo / tiempo real | Subasta dinámica ascendente: unirse a una subasta abierta y pujar en vivo | Toda entrada a la sala se gatea por `isAuctionLive` (fecha=hoy y hora pasada); todas las subastas son ≥ hoy+10 días por `CHECK`+`create_subasta` → nunca "live" | Pendiente (end-to-end) | Bloquea demo del núcleo del TPO | `subasta_service.create_subasta`, schema `subastas.fecha` | `auctionSchedule.ts`, `live.tsx`, `subasta/[id]`, `subastas.tsx` | `db` CHECK fecha; seed | Permitir/seedear una subasta "hoy" para demo y/o relajar el gating de entrada a `estado='abierta'` |
| A2 | P0 | Admin / empresa | Empresa verifica usuarios, medios, evalúa artículos, crea/cierra subastas | Endpoints y UI admin existen pero exigen `usuarioId == 12`, que **no existe** en el seed; empleados no loguean | Pendiente (datos) | Bloquea todos los flujos admin y la aprobación de registros | `dependencies.require_admin`, `auth_service.login` | `profile.tsx` (`id===12`), `app/admin/*` | seed sin cliente 12 | Seedear un cliente admin id 12 con credenciales (o mover admin a rol en `empleados`/flag) |
| A3 | P0 | Registro 2 etapas | Empresa evalúa y habilita; recién ahí el usuario crea clave | Paso 1 deja `pendiente` (correcto); aprobación exige admin → sin admin usable (A2), nadie aprueba | Parcial | Nuevo usuario no puede completar registro en demo | `admin.verify_user` | `register-step2` | — | Depende de A2; documentar usuario demo aprobado (ya hay `DEMO-POSTOR-*`) |
| B1 | P1 | Cierre de subasta | Cuando nadie puja más, se cierra y se generan ventas/pagos | Solo cierre manual admin; sin scheduler ni apertura/cierre por horario | Parcial | Ciclo no fluye solo; con A1/A2 el cierre no es operable en demo | `subasta_service.cerrar_subasta` | `admin/auctions` | — | Documentar cierre manual como decisión, o agregar job/endpoint operable por admin demo |
| B2 | P1 | Empresa compra sin pujas | Si nadie puja, la empresa compra al precio base al finalizar | `cerrar_subasta` solo notifica al dueño; no registra venta, no cambia dueño, no paga al consignante | Parcial | Regla de negocio incompleta; afecta trazabilidad de ventas | `cerrar_subasta` | — | `registrodesubasta` | Registrar la "compra empresa" (venta + liquidación al consignante) o documentar alcance |
| C1 | P2 | Liquidación al consignante | El dinero de lo vendido va a una cuenta a la vista (puede del exterior) declarada | Existe `medios_pago.es_cuenta_receptora`; no hay flujo donde el dueño cobre | Pendiente | Cierra el circuito del consignante; no central para demo | — | — | `es_cuenta_receptora` | Documentar fuera de alcance o agregar vista de liquidación |
| C2 | P2 | Subasta "colección" | Juntar muchos artículos de un dueño bajo su nombre | No existe | Pendiente | Bajo | — | — | — | Documentar explícitamente fuera de alcance |
| C3 | P2 | `verify-email` | (Derivado) verificación de email | Endpoint `POST /auth/verify-email` con cuerpo vacío (`pass`) | Dudoso | Bajo (cubierto por token de paso 2) | `auth.verify_email` | — | Swagger lo lista | Borrar el stub o documentar que el email se valida vía token de paso 2 |

## 4. Detalle por faltante (P0 / P1)

### A1 — El circuito en vivo es inalcanzable desde la app

- **Qué pide la consigna:** modalidad *dinámica ascendente*; el usuario elige una subasta **abierta**, se conecta, ve la mayor oferta y puja en tiempo real recibiendo las pujas de los demás.
- **Evidencia en código:**
  - [auctionSchedule.ts:38-47](../../frontend-da1/src/utils/auctionSchedule.ts#L38-L47): `isAuctionLive` → `"live"` solo si `isSameLocalDate(scheduledAt, now)` **y** la hora ya pasó.
  - [live.tsx:104](../../frontend-da1/app/(tabs)/live.tsx#L104): el lobby muestra solo `subastas.filter((s) => isAuctionLive(s))`.
  - [subasta/[id]/index.tsx:201,411](../../frontend-da1/app/subasta/[id]/index.tsx#L411): el botón "Ingresar a la Sala" solo aparece si `isLive`.
  - [subasta_service.py:70-75](app/services/subasta_service.py#L70-L75): `create_subasta` exige `fecha > hoy + 10 días`; el seed pone todas las subastas a +15..+60 días.
- **Por qué el estado actual no alcanza:** ninguna subasta puede tener `fecha = hoy`, así que `isAuctionLive` nunca es verdadero → el lobby siempre queda vacío y el detalle nunca ofrece entrar. El backend sí permite `join`/`puja`/`stream` sobre cualquier subasta `abierta` (no chequea la fecha), pero **la UI no da forma de llegar ahí**. Es el caso "parece tenerlo pero no funciona end-to-end".
- **Impacto:** no se puede demostrar el núcleo del TPO (puja en vivo + SSE) sin editar la DB a mano. Riesgo alto en la entrega final.
- **Archivos a revisar:** `src/utils/auctionSchedule.ts`, `app/(tabs)/live.tsx`, `app/subasta/[id]/index.tsx`, `app/(tabs)/subastas.tsx`, `db/seed_subastas_demo.sql`, `app/services/subasta_service.py`.
- **Propuesta (sin implementar):** opción mínima para demo → seedear (o permitir crear) **una** subasta con `fecha = hoy` y hora pasada, aceptando saltar el `CHECK`/regla de +10 días para ese dato de demo. Opción robusta → desacoplar "elegibilidad de entrada a sala" de la fecha exacta: permitir entrar a cualquier subasta `estado='abierta'` (o agregar un estado/flag `en_vivo` que el admin active al iniciar la subasta presencial), que es lo más fiel a "el usuario selecciona a cuál de las subastas abiertas conectarse".
- **Validación manual sugerida:** con una subasta de hoy, abrir tab En Vivo → debe listarse → unirse → pujar desde dos cuentas y ver la puja del otro sin refrescar.
- **Tests mínimos:** unit de `getAuctionScheduleStatus` con fecha hoy/pasada/futura; e2e manual de dos clientes recibiendo broadcast.

### A2 — No existe un usuario admin usable

- **Qué pide la consigna:** la empresa verifica usuarios y medios, evalúa artículos, arma catálogos y cierra subastas.
- **Evidencia en código:**
  - [dependencies.py:33-38](app/dependencies.py#L33-L38): `require_admin` rechaza salvo `usuarioId == 12`.
  - [profile.tsx:1369](../../frontend-da1/app/(tabs)/profile.tsx#L1369): el panel admin solo aparece si `user?.id === 12`.
  - `db/seed_subastas_demo.sql`: crea `empleados` 900001/900010 (sin `personas_adicionales` → sin email/clave) y `clientes` 900006-900009. **No hay cliente id 12.**
  - [auth_service.py:73-76](app/services/auth_service.py#L73-L76): el login JOINea `personas`+`clientes` y exige `admitido='si'`; los empleados no son clientes → no pueden loguear.
- **Por qué no alcanza:** salvo que la base de producción tenga un cliente id 12 con credenciales conocidas (no está en el repo ni documentado), **nadie puede operar como admin** ni aprobar registros.
- **Impacto:** bloquea A3 (aprobación de registro), verificación de medios, evaluación de artículos, alta/cierre de subastas. Riesgo de seguridad/operación alto.
- **Archivos a revisar:** `app/dependencies.py`, `db/seed_subastas_demo.sql`, `app/services/auth_service.py`, `frontend-da1/app/(tabs)/profile.tsx`.
- **Propuesta (sin implementar):** para demo → seedear un cliente id 12 (`admitido='si'`, `estado_registro='aprobado'`, password hash conocido) y documentar sus credenciales junto a los `DEMO-POSTOR-*`. Robusto → modelar admin por rol real (flag en `empleados`/`clientes`) y derivarlo en el JWT en vez de hardcodear `12`.
- **Validación manual:** loguear como admin demo → ver "Panel de Administración" → aprobar un registro pendiente → confirmar que el usuario luego completa paso 2 y loguea.
- **Tests mínimos:** `require_admin` 403 para común y OK para id admin; login del admin demo OK.

### A3 — Registro en dos etapas sin aprobador disponible

- **Qué pide la consigna:** datos+DNI → la empresa evalúa e investiga → asigna categoría → mail con código → el usuario crea su clave → registra medio de pago.
- **Evidencia en código:** [auth.py:48-94](app/api/auth.py#L48-L94) `registro_paso1` deja la solicitud **pendiente** (correcto, ya no auto-aprueba) y devuelve "la empresa revisará tus datos"; la aprobación vive solo en [admin.py:29-65](app/api/admin.py#L29-L65) (`verify_user`, exige admin + categoría + manda email con token). Paso 2 ([auth.py:97-111](app/api/auth.py#L97-L111)) setea clave y medio inicial.
- **Por qué no alcanza:** el flujo es correcto, pero **depende de A2**: sin admin usable, ningún registro nuevo se aprueba → el usuario queda trabado. Para la demo conviene mostrar el camino completo con un admin real.
- **Impacto:** medio/alto en demo de onboarding; nulo si se usan los `DEMO-POSTOR-*` ya aprobados en el seed.
- **Archivos a revisar:** `app/api/admin.py`, `app/api/auth.py`, pantallas `(auth)/register-step*`.
- **Propuesta:** resolver A2 y guionar la demo: registrar uno nuevo → aprobarlo como admin → completar paso 2.
- **Tests mínimos:** paso1 deja pendiente; login pendiente 403; admin aprueba → token → paso2 OK.

### B1 — Cierre de subasta solo manual, sin coherencia temporal

- **Qué pide la consigna:** cuando ya nadie puja más, el último postor gana, se registra la venta, se genera el pago y se notifica.
- **Evidencia:** [subastas.py:242-257](app/api/subastas.py#L242-L257) `close_auction` (require_admin) y [subasta_service.py:551-624](app/services/subasta_service.py#L551-L624) `cerrar_subasta` hacen bien ganador+venta+pago+notificación. No hay scheduler ni cierre por horario (confirma `08_PENDING_CONTEXT`).
- **Por qué no alcanza:** combinado con A1 (subastas siempre futuras) y A2 (sin admin), el ciclo "abre→puja→cierra→pago" no se puede recorrer fluido. La lógica de cierre en sí es correcta.
- **Impacto:** P1 — para demo controlada basta cierre manual por admin, pero requiere A2.
- **Propuesta:** documentar cierre manual como decisión de diseño y asegurar que el admin demo pueda dispararlo; opcional job de cierre por fecha/hora.
- **Tests mínimos:** cierre genera pagos correctos; no-admin 403 (ya cubierto).

### B2 — "Empresa compra al precio base" incompleto

- **Qué pide la consigna:** si nadie puja por un artículo, la empresa lo compra al valor base al finalizar la subasta.
- **Evidencia:** [subasta_service.py:597-604](app/services/subasta_service.py#L597-L604): para ítems sin pujas, `cerrar_item(..., None)` + notificación al dueño. **No** crea `registrodesubasta`, no cambia dueño, no liquida al consignante.
- **Por qué no alcanza:** la "compra por la empresa" queda como aviso, no como transacción. Afecta trazabilidad de ventas y el circuito del consignante.
- **Impacto:** P1/P2 — no rompe la demo de puja, pero es una regla explícita de la consigna sin cerrar.
- **Propuesta:** registrar la compra de la empresa como venta (con la empresa como comprador) y disparar la liquidación al consignante, o documentar el alcance.
- **Tests mínimos:** cierre con ítem sin pujas → registro de venta a empresa + notificación.

## 5. Cosas que revisé y NO considero faltantes importantes

- **Registro auto-aprobado, guard admin, idempotencia de pujas, SSE en frontend, pago de multas, garantía/límite reservado, moneda real por subasta, UI admin, UI de pago, seguimiento de consignación (aceptar tasación / aumentar seguro), mejora automática de categoría:** todos figuran como pendientes/parciales en `14_*` pero **ya están implementados y verificados en código**. El backlog `14` quedó desactualizado.
- **Idempotencia:** implementada con tabla/migración (`db/migration_p0_3_puja_idempotency.sql`), header leído en `place_bid`, replay cacheado. OK.
- **Validación de pago** (`confirmar_pago`): valida pertenencia del medio, `validado`, moneda y fondos vs `limite_reservado`, retiro fuerza pérdida de seguro, envío exige dirección + costo. OK.
- **Acceso al stream:** `validar_acceso_stream` chequea abierta/categoría/medio/sesión. OK.
- **Deploy:** `.env` del front apunta al backend online; localhost queda comentado. OK.
- **Costo de envío fijo (500):** decisión documentada; suficiente para demo.
- **`datos_encriptados` sin cifrado real, CORS abierto, `SECRET_KEY` default:** deuda de seguridad real pero no rompe funcionalidad de demo; mantener en checklist de hardening, no es "faltante funcional".
- **Subasta colección / liquidación al consignante / `verify-email` stub:** menores o documentables fuera de alcance (C1/C2/C3).

## 6. Próximo backlog recomendado

### P0 recomendado

1. **Seed + admin demo operable (A2/A3).**
   - *Objetivo:* que exista un admin logueable (id 12 o rol real) y datos para recorrer aprobación de registro, verificación de medios, evaluación de artículos.
   - *Por qué importa:* desbloquea todos los flujos de empresa y el onboarding.
   - *Archivos:* `db/seed_subastas_demo.sql`, `app/dependencies.py` (si se pasa a rol), `auth_service.py`.
   - *Orden:* primero. *Requiere:* DB (seed) + back si se modela rol.
2. **Hacer jugable el live para demo (A1).**
   - *Objetivo:* poder entrar a una sala y pujar en vivo desde la app.
   - *Por qué importa:* es el núcleo del TPO y hoy es inalcanzable por gating de fecha.
   - *Archivos:* `db/seed_subastas_demo.sql` (subasta de hoy) y/o `src/utils/auctionSchedule.ts` + entradas de `live.tsx`/detalle; revisar regla +10 días en `subasta_service.py`.
   - *Orden:* segundo. *Requiere:* DB + frontend (y back si se relaja la regla).
3. **Recorrido de cierre→pago operable (B1).**
   - *Objetivo:* admin cierra una subasta con pujas y el ganador paga desde la app.
   - *Archivos:* `app/admin/auctions.tsx`, `subasta_service.cerrar_subasta` (ya OK), `app/pagos/[subastaId].tsx`.
   - *Orden:* tercero. *Requiere:* depende de P0.1 (admin) y datos.

### P1 recomendado

1. **Completar "empresa compra al precio base" (B2).** Registrar venta/liquidación o documentar alcance. *Back + DB.*
2. **Cierre por horario (opcional) o documentar cierre manual (B1).** Decisión de equipo. *Back.*
3. **Hardening de entrega:** `SECRET_KEY` por env, acotar CORS, confirmar 1 worker para SSE en Render. *Back/infra.*

## 7. Veredicto final

- **¿La app cumple lo importante de la consigna?** **Parcial — y más cerca de lo que sugiere el backlog viejo.** La lógica de negocio central (registro 2 etapas, pujas con reglas 1%/20% y premium, idempotencia, SSE, multas/bloqueo, garantía, pagos, consignación, categorías) está implementada y es correcta en código. Lo que falla es la **operabilidad de la demo end-to-end**: datos y entrada al live.
- **¿Qué faltaría sí o sí antes de entregar?**
  1. Un **admin demo logueable** (hoy no existe usuario id 12) — sin esto no se opera ni se aprueban registros.
  2. **Una subasta efectivamente "en vivo"** alcanzable desde la UI — hoy el gating de fecha + la regla de +10 días lo impiden, dejando inaccesible el núcleo del TPO.
  3. Que con esos dos arreglos se pueda recorrer **abrir → pujar en vivo → cerrar → pagar** en la demo.
- **¿Qué se puede dejar documentado como limitación?** Subasta "colección" (no implementada), liquidación al consignante / cuenta receptora del exterior, "empresa compra al precio base" como solo-notificación, cierre solo manual (sin scheduler), `verify-email` stub, y la deuda de seguridad (cifrado de medios, CORS, SECRET_KEY). Ninguna rompe la demo si se explicita.
</content>
</invoke>
