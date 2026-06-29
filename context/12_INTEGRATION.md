# 12 · Integración con `frontend-da1`

Vista desde el **backend**. (La contraparte está en `frontend-da1/context/11_INTEGRATION.md`.)

## Relación

- `frontend-da1` es una app **Expo / React Native (TypeScript)** que consume esta API por **HTTP REST con JWT Bearer**.
- Son **dos repos git independientes** (remotes `TomasBasualdo1/backend-da1` y `.../frontend-da1`), abiertos juntos en el workspace VS Code. **No es un monorepo**: no comparten build ni package manager.
- **Contrato compartido**: `docs/Swagger_v5.YAML`. De ahí se generaron los modelos Pydantic (`app/schemas/schemas.py`) y los tipos TS (`frontend-da1/src/types/`). El mismo `Swagger_v5.YAML` está copiado en `frontend-da1/context/`.
- El esquema SQL también está duplicado: `db/Estructura-PostgreSQL-da1-updated.sql` ≈ `frontend-da1/context/Estructura-PostgreSQL-da1-updated.sql`.

## Cómo se conectan

- El frontend usa `axios` con `baseURL = process.env.EXPO_PUBLIC_API_URL` (en `frontend-da1/.env`), fallback `http://localhost:8000`.
- Interceptor del front agrega `Authorization: Bearer <token>` desde SecureStore; ante **401** borra el token y redirige a login.
- CORS del backend está abierto (`allow_origins=["*"]`), por eso el front puede consumir desde web/emulador sin fricción.

## Mapa servicio TS → endpoints backend

| Servicio front (`src/services/`) | Endpoints backend |
|----------------------------------|-------------------|
| `authService.ts` | `/auth/*`, `/paises` |
| `userService.ts` | `/usuarios/me*`, multas, notificaciones |
| `auctionService.ts` | `/subastas/*`, `/admin/subastas*` |
| `articleService.ts` | `/articulos/*` |

## Contrato: detalles que importan

- **Registro paso 1** y **update perfil** y **publicar artículo** van como `multipart/form-data` (el front arma `FormData` con `uri/name/type` para RN). Los nombres de campo deben coincidir exactamente (`fotoFrente`, `fotoDorso`, `fotos`, `documentacionOrigen`).
- El front **normaliza** respuestas tolerando camelCase y snake_case (`normalizeUsuario`, `normalizeArticulo`, etc.), porque el backend no es 100% consistente. Si cambiás nombres de campos en responses, revisá esos normalizers.
- El front manejal códigos: 401 (sesión), 403 (acceso/categoría), 409 (ya conectado a otra subasta en vivo) — mantené esos códigos.

## Desalineaciones conocidas (importante)

1. **SSE no consumido**: el backend expone `/subastas/{id}/stream`, pero el frontend **no abre EventSource** todavía. `live.tsx` no se actualiza en tiempo real (usa carga puntual y un timer hardcodeado `31:59`). Integrar SSE es trabajo pendiente.
2. **Idempotency-Key**: el front envía el header en `pujar()`, el backend lo **ignora**. No hay deduplicación.
3. **Admin sin UI dedicada**: `auctionService` tiene `createSubasta`/`addCatalogItem` (apuntan a `/admin/*`), pero no se detectó pantalla admin en el front. Backend tampoco protege bien esos endpoints (ver [10_API_REFERENCE.md](10_API_REFERENCE.md)).

> Al cambiar el contrato (rutas, payloads, nombres de campos), **actualizá ambos repos** y el Swagger. No rompas un lado en silencio.
