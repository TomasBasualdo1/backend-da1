# 29 · Diagnóstico: ganador de ítem y pago desde perfil

Fecha: 2026-06-28

## 1. Qué ocurre hoy cuando un usuario gana un artículo

El backend adjudica el ítem cuando un admin llama `POST /subastas/{id}/cerrar`. En el código actual ese endpoint cierra el ítem activo, no toda la subasta de golpe. Si el ítem tiene pujas, se marca la mejor puja como ganadora, se marca el ítem como subastado, se registra la venta, se genera o actualiza un pago pendiente para el ganador y se crea una notificación privada.

En frontend, la sala en vivo ya abre SSE y reacciona a eventos `puja`, `item` y `cierre`, pero el evento `item` solo refresca detalle/historial y avanza al siguiente ítem. No muestra un cartel específico al usuario ganador.

## 2. Cuándo se define oficialmente que ganó

Se define al cerrar el ítem activo en `SubastaService.cerrar_subasta`, no al finalizar toda la subasta. La subasta queda abierta si todavía hay ítems pendientes; recién se marca `subastas.estado = 'cerrada'` cuando ya no queda próximo ítem activo.

## 3. SSE cuando gana un usuario

Sí se emite SSE, pero de forma general. El router emite un evento `item` con `itemCerrado`, `itemActivo`, `itemsPendientes` y `subastaCerrada`. Dentro de `itemCerrado` viaja `clienteGanador`, `pujaId` e `importe`, por lo que el frontend puede determinar si el ganador es el usuario actual.

No existe un evento privado `ganador` ni un toast/modal implementado en la app para ese caso.

## 4. Notificación para el ganador

Sí. Al cerrar un ítem con puja ganadora, el backend crea una notificación tipo `subasta` para `cliente_ganador` con un mensaje del estilo: ganó el ítem, importe, comisión y plazo de 72 hs.

## 5. Pago/deuda para el ganador

Sí. Al cerrar un ítem con ganador, el backend llama `SubastaRepository.generar_pago`.

## 6. Granularidad del pago

El pago se modela por `subasta_id + cliente_id`. Si el mismo usuario gana más de un ítem de la misma subasta y el pago sigue pendiente, `generar_pago` acumula `total_pujado`, `comision` y `total_final` en el mismo pago en lugar de insertar otro. Si ganan usuarios distintos, hay un pago por usuario ganador.

Las ventas de cada ítem quedan separadas en `registrodesubasta`.

## 7. Endpoint para saber que el usuario ganó

Durante la sala en vivo puede usarse el SSE `GET /subastas/{id}/stream`, evento `item`, comparando `event.data.itemCerrado.clienteGanador` contra `user.id`.

Fuera de la sala, el endpoint existente `GET /usuarios/me/notificaciones` permite ver la notificación privada. Para pago por subasta existe `GET /subastas/{id}/pagos`, pero exige conocer `subastaId`.

## 8. Endpoint para pagos pendientes en perfil

Hoy no hay un endpoint global de perfil para listar pagos pendientes del usuario. El único endpoint de deuda de subasta es `GET /subastas/{id}/pagos`, que sirve si la app ya sabe qué subasta consultar.

## 9. Pantalla/sección en perfil

Existe la pestaña `Pagos y Multas` en `app/(tabs)/profile.tsx`, pero hoy solo muestra medios de pago y multas. No muestra artículos ganados, pagos pendientes de subasta ni una acción global para ir a pagar una compra ganada.

También existe `app/pagos/[subastaId].tsx`, que ya resuelve el flujo de pago de una subasta cuando se le pasa el `subastaId`.

## 10. Dónde está el problema

Es una combinación:

- Backend: la adjudicación, notificación y pago existen, pero falta un endpoint de perfil que exponga compras/pagos pendientes con sus ítems ganados sin conocer previamente el `subastaId`.
- Contrato API: `Pago` no trae detalle de artículos ganados ni una variante para perfil.
- Frontend live: escucha SSE, pero no muestra alerta privada cuando el evento `item` indica que el usuario actual ganó.
- Frontend perfil/navegación: no consulta pagos pendientes ni muestra “Artículos ganados” / “Pagos pendientes”.
- Demo/seed: no es la causa principal. El backend ya puede generar pagos al cerrar ítems y el seed tiene un pago pendiente demo, pero la app no lo descubre desde perfil.

## 11. Solución mínima recomendada

1. Agregar un endpoint autenticado de perfil, `GET /usuarios/me/pagos-pendientes`, que devuelva pagos pendientes del usuario con subasta, totales, fecha límite y lista de ítems ganados desde `registrodesubasta`.
2. Filtrar ese endpoint por `pagos.estado = 'pendiente'` y `subastas.estado = 'cerrada'` para que el pago aparezca en perfil cuando la subasta haya finalizado completamente.
3. Reutilizar `app/pagos/[subastaId].tsx` para pagar, navegando desde cada pago pendiente.
4. En `live.tsx`, usar el evento SSE `item` ya existente y mostrar `Alert.alert` solo si `itemCerrado.clienteGanador === user.id`. Deduplicar por ítem cerrado para no repetir alertas ante reconexiones o refetch.
5. Mantener el pago agregado por subasta/cliente para no duplicar deudas, y usar `registrodesubasta` como detalle de artículos ganados.

Esta opción no requiere migración, respeta la arquitectura `API -> service -> repository`, reutiliza la pantalla de pago existente y no cambia reglas de negocio ajenas.
