# 28 · Diagnóstico: avance de ítems en subastas

Fecha: 2026-06-28

## 1. Cómo funciona hoy una subasta con varios ítems

- Una subasta tiene uno o más catálogos (`catalogos`) y cada catálogo tiene ítems (`itemscatalogo`) asociados a productos.
- Cada ítem tiene `preciobase`, `comision` y `subastado` (`si`/`no`).
- Las pujas se registran en `pujos` contra un `item` específico, no contra la subasta completa.
- El detalle autenticado (`GET /subastas/{id}`) devuelve todo el catálogo con `mejorOfertaActual` calculada por ítem.
- El historial (`GET /subastas/{id}/historial`) devuelve pujas de toda la subasta, incluyendo `itemId`.

## 2. Dónde se define el ítem actual

No existe hoy una columna, tabla, estado ni endpoint que persista o exponga explícitamente el "ítem actual".

En frontend, `app/(tabs)/live.tsx` define localmente `currentItem` como el primer elemento del catálogo con `subastado === "no"` al unirse a la sala. Ese valor no se sincroniza con un evento de cambio de ítem porque el backend no emite evento `item` en el flujo actual.

En backend, `procesar_puja` acepta cualquier `item_id` válido de la subasta mientras `itemscatalogo.subastado = 'no'`. Por lo tanto, hoy el backend no restringe pujas al primer ítem pendiente ni a ningún ítem activo.

## 3. Cómo se registra una puja

`POST /subastas/{id}/items/{item_id}/pujar` llama a `SubastaService.procesar_puja`.

El service valida:

- usuario unido a la subasta;
- ítem existente en esa subasta con `SELECT ... FOR UPDATE`;
- ítem no subastado;
- reglas de importes 1% mínimo / 20% máximo para no premium;
- regla premium para oro/platino;
- garantía/límite reservado;
- idempotencia por `Idempotency-Key`.

Luego `SubastaRepository.registrar_puja` inserta en `pujos (asistente, item, importe, ganador)` con `ganador = 'no'`.

Conclusión: la puja queda correctamente asociada al ítem, no a la subasta genérica.

## 4. Cómo se define el ganador de un ítem hoy

Durante `cerrar_subasta`, `SubastaRepository.obtener_items_con_pujas` recorre cada ítem pendiente (`ic.subastado = 'no'`) y para cada uno toma su mejor puja mediante un `LEFT JOIN LATERAL` ordenado por `pu.importe DESC`.

Si hay puja, `cerrar_item` marca `itemscatalogo.subastado = 'si'` y marca esa puja como `ganador = 'si'`. Si no hay puja, marca el ítem como subastado sin puja ganadora.

## 5. Qué hace exactamente `cerrar_subasta`

El comportamiento actual cierra todos los ítems pendientes de la subasta en una sola operación:

1. Busca la subasta y rechaza si ya está cerrada.
2. Obtiene todos los ítems no subastados con su mejor puja.
3. Para cada ítem con puja:
   - marca solo ese ítem como subastado;
   - marca la mejor puja de ese ítem como ganadora;
   - registra una venta en `registrodesubasta`;
   - acumula deuda por cliente;
   - notifica al ganador.
4. Para cada ítem sin pujas:
   - marca ese ítem como subastado;
   - notifica al dueño que la empresa lo adquirió al precio base.
5. Genera un pago agregado por cliente ganador.
6. Marca la subasta como `cerrada`.
7. Finaliza las sesiones.
8. El router emite un evento SSE `cierre`.

## 6. La sospecha es real, parcial o distinta

Es parcial y distinta:

- Confirmado: no hay avance real de ítem activo. La subasta no tiene un "ítem actual" backend y el frontend queda con una selección local.
- Confirmado: se puede pujar por cualquier ítem no subastado si se conoce el `item_id`.
- Confirmado: al cerrar, el backend cierra todos los ítems pendientes de golpe, por lo que no hay adjudicación parcial seguida de avance al siguiente ítem.
- No confirmado como bug backend actual: que el ganador del primer ítem quede asociado automáticamente a todos los demás. El SQL de cierre calcula la mejor puja por cada `pu.item`, por lo que cada ítem con pujas tiene su propio ganador. Los ítems sin pujas no reciben el ganador del primero.

## 7. Dónde está el bug

Principalmente en backend y contrato de flujo:

- Backend: falta definición/restricción de ítem activo y cierre parcial de ítem.
- SSE/contrato: Swagger enumera evento `item`, pero el backend no lo emite al avanzar.
- Frontend: `live.tsx` puede mostrar un `currentItem`, pero lo deriva localmente y no recibe cambio de ítem activo desde backend.
- Seed/demo: no define estado de ítem activo; no es la causa principal.

## 8. Endpoints/responses que usa el frontend

`frontend-da1/src/services/auctionService.ts` consume:

- `GET /subastas` para listar subastas.
- `GET /subastas/{id}` para detalle con `catalogo`, `precioBase`, `mejorOfertaActual`, `limiteMinimo`, `limiteMaximo`, `subastado`.
- `POST /subastas/{id}/join` para unirse.
- `GET /subastas/{id}/stream` para SSE.
- `GET /subastas/{id}/historial` para pujas por subasta.
- `POST /subastas/{id}/items/{itemId}/pujar` para pujar sobre `currentItem.id`.

El artículo actual en la sala sale hoy de `detalle.catalogo.find((i) => i.subastado === "no")`.

## 9. Riesgos al tocar el flujo

- Pagos: `generar_pago` evita duplicados por subasta/cliente, pero si el cierre pasa a ser parcial hay que acumular importes sin perder ítems ganados después.
- Notificaciones: un cierre parcial no debe reenviar notificaciones de ítems ya cerrados.
- Ventas: `registrodesubasta` no debe duplicarse ante reintentos; cerrar solo ítems `subastado = 'no'` reduce el riesgo.
- SSE: mantener `puja` sin duplicados en replay idempotente y agregar `item` sin romper `cierre`.
- Frontend: si no recibe `item`, seguirá viendo el ítem anterior hasta refetch/polling.
- Demo Swagger: `POST /subastas/{id}/cerrar` cambiaría de cierre total a cierre progresivo si se reutiliza el endpoint existente; hay que documentarlo.

## 10. Alternativa recomendada

Recomiendo una solución mínima sin migración:

1. Definir el ítem activo como el primer `itemscatalogo` no subastado de la subasta, ordenado por `ic.identificador`.
2. Ordenar siempre el catálogo por `ic.identificador` para que backend y frontend deriven el mismo ítem.
3. Rechazar pujas sobre ítems no activos aunque pertenezcan a la subasta.
4. Cambiar el cierre administrativo para cerrar solo el ítem activo en cada llamada.
5. Si queda otro ítem pendiente, mantener la subasta abierta y emitir SSE `item` con el siguiente ítem activo.
6. Si no queda ningún ítem pendiente, marcar la subasta como cerrada, finalizar sesiones y emitir SSE `cierre`.
7. Mantener las pujas, ventas, pagos y notificaciones asociadas al ítem cerrado, sin tocar otros ítems.

Esta alternativa usa el modelo existente (`subastado`) y evita agregar columna de "ítem actual". Una migración solo sería necesaria si el equipo quiere permitir saltos manuales, reordenamiento del catálogo o recuperación exacta de un ítem activo distinto del primer pendiente.
