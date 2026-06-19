# Architecture

## Stack Tecnológico

- **Frontend:** React Native con Expo.
- **Backend:** FastAPI (Python).
- **Base de Datos & Almacenamiento:** Supabase (PostgreSQL + Storage para fotos de documentos y artículos).

## Patrones de Comunicación

- **REST API:** Para todo el CRUD transaccional (Auth, Perfil, Consignación) respetando la convención OpenAPI 3.0 definida.
- **Server-Sent Events (SSE):** Utilizado para el servicio de streaming en tiempo real [cite: 27] a través del endpoint `/subastas/{id}/stream` para emitir eventos de tipo `puja` o `item`.
- **Autenticación:** JWT vía cabeceras `Bearer`.

## Flujo de Concurrencia

Para garantizar la integridad en el Motor de Pujas, FastAPI implementará validación por `Idempotency-Key` y bloqueos transaccionales (pessimistic locking) en PostgreSQL, evitando que procese pujas simultáneas[cite: 51].
