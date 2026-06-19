# 10 · API Reference

Rutas reales montadas en `app/api/router.py`. Contrato formal completo: `docs/Swagger_v4.YAML`. Modelos: `app/schemas/schemas.py`.

- **Auth**: header `Authorization: Bearer <jwt>`. El JWT trae `usuarioId`, `categoria`, `admitido`, `jti`, `exp`.
- **Base URL** local: `http://127.0.0.1:8000`. Prod (frontend): host tipo `backend-da1.onrender.com`.
- Columna *Auth*: 🔓 público · 🔒 requiere token · 👑 requiere admin (`usuarioId == 1`).

## Root
| Método | Ruta | Auth | Archivo |
|--------|------|------|---------|
| GET | `/` | 🔓 | `main.py` (healthcheck simple) |

## Autenticación — `app/api/auth.py` (prefix `/auth`)
| Método | Ruta | Auth | Body | Respuesta |
|--------|------|------|------|-----------|
| POST | `/auth/registro/paso1` | 🔓 | **multipart**: documento, nombre, apellido, email, direccion, numeroPais, telefono?, fotoFrente(file), fotoDorso(file) | 201 · ⚠ **auto-aprueba** (ver 07/08) |
| POST | `/auth/registro/paso2` | 🔓 | json: token, password, payment*? | 201 |
| POST | `/auth/login` | 🔓 | json: documento, password | `TokenResponse` (access_token) |
| POST | `/auth/logout` | 🔒 | — | `LogoutResponse` (blacklistea jti) |
| POST | `/auth/verify-email` | 🔓 | — | **stub vacío (`pass`)** — no implementado |
| POST | `/auth/forgot-password` | 🔓 | json: email | mensaje genérico (no revela existencia) |
| POST | `/auth/reset-password` | 🔓 | json: token, newPassword | mensaje |

## Perfil — `app/api/usuarios.py` (prefix `/usuarios`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| GET | `/usuarios/me` | 🔒 | → `Usuario` |
| PATCH | `/usuarios/me` | 🔒 | **multipart**: nombre?, apellido?, direccion?, telefono?, foto?(file) |
| DELETE | `/usuarios/me/foto` | 🔒 | borra foto de perfil |
| GET | `/usuarios/me/medios-pago` | 🔒 | → `list[MedioPago]` |
| POST | `/usuarios/me/medios-pago` | 🔒 | `MedioPagoInput` → 201 |
| PATCH | `/usuarios/me/medios-pago/{id}` | 🔒 | `MedioPagoUpdate` |
| DELETE | `/usuarios/me/medios-pago/{id}` | 🔒 | 204 |
| GET | `/usuarios/me/metricas` | 🔒 | → `UsuarioMetricas` |
| GET | `/usuarios/me/multas` | 🔒 | → `list[Multa]` |
| POST | `/usuarios/me/multas/pagar` | 🔒 | `MultaPagoRequest` (multaId, medioPagoId) |

## Notificaciones — `app/api/notificaciones.py` (prefix `/usuarios`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| GET | `/usuarios/me/notificaciones` | 🔒 | → `list[Notificacion]` |
| POST | `/usuarios/me/notificaciones/{id}/leer` | 🔒 | marca leída |

## Subastas — `app/api/subastas.py` (prefix `/subastas`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| GET | `/subastas/publicas` | 🔓 | → `list[SubastaListadoPublico]` |
| GET | `/subastas/publicas/{id}` | 🔓 | → `SubastaDetallePublica` (sin precios sensibles) |
| GET | `/subastas` | 🔒 | → `list[SubastaListado]` |
| GET | `/subastas/{id}` | 🔒 | → `SubastaDetalle` (con catálogo) |
| POST | `/subastas/{id}/join` | 🔒 | 201 — valida categoría/medios/sesión |
| DELETE | `/subastas/{id}/join` | 🔒 | 204 |
| GET | `/subastas/{id}/stream` | 🔒 | **SSE** (`text/event-stream`); eventos `puja`/`cierre` |
| POST | `/subastas/{id}/items/{item_id}/pujar` | 🔒 | `PujaRequest` (importe) → `PujaResponse`; 201 |
| GET | `/subastas/{id}/historial` | 🔒 | → `list[Puja]` |
| GET | `/subastas/{id}/pagos` | 🔒 | → `Pago` (404 si no hay deuda) |
| POST | `/subastas/{id}/pagos` | 🔒 | `PagoRequest` (medioPagoId, modoEntrega, direccionEnvio?, aceptaPerderSeguro?) |
| POST | `/subastas/{id}/cerrar` | 🔒 | cierra subasta (⚠ no chequea admin — ver 08) |

## Artículos (consignación) — `app/api/articulos.py` (prefix `/articulos`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| POST | `/articulos` | 🔒 | multipart **o** json; `ArticuloInput` (≥6 fotos) → `Articulo` 201 |
| GET | `/articulos/mis-publicaciones` | 🔒 | → `list[Articulo]` |
| GET | `/articulos/{id}` | 🔒 | → `Articulo` (dueño o admin) |
| POST | `/articulos/{id}/aceptar-tasacion` | 🔒 | `AceptarTasacionRequest` (acepta) → crea producto si acepta |
| POST | `/articulos/{id}/seguro/aumentar` | 🔒 | `SeguroAumentoRequest` (montoNuevo) |

## Administración — `app/api/admin.py` (prefix `/admin`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| POST | `/admin/usuarios/{id}/verificar` | 🔒 ⚠ | `UsuarioVerificacion` (admitido, categoria?, motivoRechazo?). **No llama `_require_admin`** |
| POST | `/admin/medios-pago/{id}/verificar` | 🔒 ⚠ | `MedioPagoVerificacion`. **No llama `_require_admin`** |
| POST | `/admin/articulos/{id}/evaluar` | 👑 | `ArticuloEvaluacion` → `Articulo`. Sí valida admin |
| POST | `/admin/subastas` | 🔒 ⚠ | `SubastaCreate` → 201. **No llama `_require_admin`** |
| POST | `/admin/subastas/{id}/catalogo/items` | 🔒 ⚠ | `CatalogoItemInput` (uno de productoId/articuloId) → 201. **No llama `_require_admin`** |

> ⚠ **Inconsistencia de seguridad**: solo `/admin/articulos/{id}/evaluar` aplica `_require_admin`. Los demás endpoints `/admin/*` quedan accesibles a cualquier usuario autenticado. Ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md).

## Uploads — `app/api/uploads.py` (prefix `/uploads`)
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| POST | `/uploads/presign` | 🔓 | genera URL firmada de Supabase (bucket `imagenes` por defecto) |
| GET | `/uploads/fotos/{id}` | 🔓 | devuelve bytes de `fotos.foto` como `image/png` |

## Países — `app/api/paises.py`
| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| GET | `/paises` | 🔓 | lista `numero, nombre, capital` |

## Formato de eventos SSE (`/subastas/{id}/stream`)
```
data: {"type": "puja", "fechaHora": "...", "data": {"itemId":..,"mejorOfertaActual":..,"limiteMinimo":..,"limiteMaximo":..,"pujaId":..}}
data: {"type": "cierre", "fechaHora": "...", "data": {"message":"...","itemsCerrados":N}}
: keepalive            (cada 30s si no hay eventos)
```
