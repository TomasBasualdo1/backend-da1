# backend-da1 — Documentación del Backend

Sistema de subastas online con API REST construida en **FastAPI** (Python 3.12+), conectada a **Supabase** (PostgreSQL + Storage).

---

## Tabla de Contenidos

- [Tech Stack](#tech-stack)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Arquitectura](#arquitectura)
- [Base de Datos](#base-de-datos)
- [Endpoints de la API](#endpoints-de-la-api)
- [Autenticación y Seguridad](#autenticación-y-seguridad)
- [Servicios y Repositorios](#servicios-y-repositorios)
- [Configuración](#configuración)
- [Cómo ejecutar](#cómo-ejecutar)
- [Despliegue con Docker](#despliegue-con-docker)
- [Testing](#testing)

---

## Tech Stack

| Categoría        | Tecnología                                                  |
| ---------------- | ----------------------------------------------------------- |
| Lenguaje         | Python 3.12+                                                |
| Framework        | FastAPI 0.136.1                                             |
| Servidor ASGI    | Uvicorn 0.46.0                                              |
| Base de datos    | PostgreSQL (Supabase) via psycopg 3.2.13                    |
| Autenticación    | JWT (python-jose) + bcrypt                                  |
| Validación       | Pydantic 2.13.3 / Pydantic-Settings                         |
| Storage          | Supabase Storage (presigned URLs via httpx)                 |
| Error Tracking   | Sentry SDK 2.58.0                                           |
| Documentación API| OpenAPI 3.0 (Swagger_v5.YAML)                               |

---

## Estructura del Proyecto

```
backend-da1/
├── main.py                          # Entry point — crea la app FastAPI
├── requirements.txt                 # Dependencias Python
├── Dockerfile                       # Imagen Docker (python:3.12-slim)
├── README.md                        # Quick start
│
├── app/
│   ├── config.py                    # Pydantic Settings (env vars)
│   ├── dependencies.py              # Inyección de dependencias (get_db, get_current_user, require_admin)
│   │
│   ├── api/                         # Controladores (route handlers)
│   │   ├── router.py                # Router principal que agrega todos los sub-routers
│   │   ├── auth.py                  # Registro paso 1/2, login, logout, forgot/reset password
│   │   ├── usuarios.py              # Perfil, medios de pago, métricas, multas, notificaciones
│   │   ├── subastas.py              # Listado, detalle, join/leave, pujas, streaming SSE, pagos, cierre
│   │   ├── articulos.py             # Publicación, mis publicaciones, tasación, seguro
│   │   ├── notificaciones.py        # Listar y marcar notificaciones
│   │   ├── admin.py                 # Admin completo: verificar usuarios, medios de pago, artículos, subastas, catalogar
│   │   ├── uploads.py               # Presigned URLs para upload a Supabase Storage
│   │   └── paises.py                # Listado de países
│   │
│   ├── core/
│   │   ├── database.py              # Conexión a PostgreSQL (psycopg, dict_row)
│   │   └── security.py              # Hashing bcrypt + creación/validación JWT
│   │
│   ├── services/                    # Capa de lógica de negocio (todos implementados)
│   │   ├── auth_service.py          # Login, logout, token blacklist
│   │   ├── usuario_service.py       # Perfil, medios de pago, métricas, multas
│   │   ├── subasta_service.py       # Subastas, join/leave, pujas, cierre, vencimientos, pagos
│   │   ├── articulo_service.py      # Publicación, tasación, seguro
│   │   ├── notificacion_service.py  # CRUD de notificaciones
│   │   ├── admin_service.py         # Verificación de usuarios, artículos, medios de pago
│   │   ├── email_service.py         # Envío de emails transaccionales (Resend / SendGrid / SMTP)
│   │   ├── streamer.py              # SubastaStreamer — SSE con eventos puja/cierre/keepalive
│   │   └── storage_service.py       # Upload de archivos a Supabase Storage
│   │
│   ├── repositories/                # Capa de acceso a datos (todos implementados)
│   │   ├── usuario_repo.py          # Consultas de usuarios, registro, verificación
│   │   ├── subasta_repo.py          # Consultas de subastas, asistentes, catálogo
│   │   ├── articulo_repo.py         # Consultas de artículos, fotos, seguros
│   │   ├── puja_repo.py             # Consultas de pujas, idempotencia
│   │   └── notificacion_repo.py     # Consultas de notificaciones
│   │
│   └── schemas/
│       └── schemas.py               # Modelos Pydantic (~470 líneas, 50+ clases)
│
├── db/
│   ├── Estructura-PostgreSQL-da1-updated.sql  # Schema completo (28 tablas)
│   ├── seed_subastas_demo.sql                 # Datos de demo para testing
│   ├── rollback_seed_subastas_demo.sql        # Rollback de datos demo
│   └── migration_p0_3_puja_idempotency.sql    # Migración de idempotencia
│
├── scripts/
│   ├── smoke_local.sh               # Smoke test contra localhost
│   └── smoke_online.sh              # Smoke test contra Render
│
├── tests/                           # Suite de tests automatizados (pytest)
│   └── test_*.py                    # Tests de vencimientos, límites de puja, idempotencia, flujos
│
├── context/                         # Documentación y consigna del TPO
│   ├── TPO_DAI_1C2026.md            # Consigna del trabajo práctico
│   ├── project-overview.md
│   ├── architecture-context.md
│   ├── code-standards.md
│   └── ai-workflow-rules.md
│
└── .env.example                     # Template de variables de entorno
```

---

## Arquitectura

El proyecto sigue una **arquitectura por capas**:

```
main.py
  └── app/api/router.py
        ├── app/api/*.py              ← Controladores (HTTP handlers)
        │     └── llaman a servicios
        ├── app/services/*.py          ← Lógica de negocio
        │     └── llaman a repositorios
        ├── app/repositories/*.py      ← Acceso a datos (SQL)
        ├── app/core/database.py       ← Conexión a DB
        ├── app/core/security.py       ← JWT + bcrypt
        └── app/dependencies.py        ← FastAPI Depends()
```

### Principios aplicados

- **Inyección de dependencias** vía `Depends()` de FastAPI
- **Repository pattern** — separación de acceso a datos y lógica de negocio
- **JWT Bearer** con blacklist de tokens en logout
- **Idempotency-Key** implementado para pujas (evita pujas duplicadas)
- **Locking pesimista** en PostgreSQL para concurrencia en pujas
- **Server-Sent Events (SSE)** implementado para bidding en tiempo real (`SubastaStreamer`) con reconexión automática

### Estado de implementación

- **52 endpoints completamente implementados** con lógica de negocio completa.
- **Todos los services y repositories** están implementados y funcionando, con validaciones de negocio, control de concurrencia e idempotencia.
- **SSE (Server-Sent Events) implementado** para bidding en tiempo real con broadcasting de pujas y cierres.
- **Suite de tests automatizados** en `tests/` ejecutables con `pytest`, validando flujos críticos: vencimientos, límites de puja, idempotencia y garantías financieras.

---

## Base de Datos

**Motor:** PostgreSQL (Supabase)

**Esquema** (`db/Estructura-PostgreSQL-da1-updated.sql`) — 28 tablas:

### Tablas principales — Identidad y Personas

| Tabla                  | Propósito                              | Claves                                   |
| ---------------------- | -------------------------------------- | ---------------------------------------- |
| `paises`               | Catálogo de países                     | numero (PK), nombre, nacionalidad        |
| `personas`             | Personas físicas base                  | identificador (PK), documento, nombre, direccion |
| `personas_adicionales` | Extensión de personas (auth, fotos)    | FK a personas, email (UNIQUE), password_hash, foto_frente, foto_dorso, token_email |
| `clientes`             | Clientes/postores                      | FK a personas, categoria, admitido       |
| `clientes_adicionales` | Extensión de clientes (registro)       | FK a clientes, estado_registro, multa_activa, bloqueado, motivo_rechazo |
| `duenios`              | Dueños/vendedores de artículos         | FK a personas, verificación financiera/judicial |
| `empleados`            | Empleados de la empresa                | FK a personas, cargo, sector             |
| `subastadores`         | Martilleros/subastadores               | FK a personas, matricula, region         |
| `sectores`             | Sectores/departamentos                 | identificador (PK), responsableSector FK |

### Tablas principales — Subastas y Catálogo

| Tabla                | Propósito                              | Claves                                   |
| -------------------- | -------------------------------------- | ---------------------------------------- |
| `subastas`           | Eventos de subasta                     | identificador (PK), fecha, hora, estado, categoria, moneda, subastador FK |
| `catalogos`          | Catálogos de subasta                   | FK a subasta + empleado responsable      |
| `itemscatalogo`      | Items dentro de un catálogo            | FK a catálogo + producto/articulo, precioBase, comision, subastado |
| `productos`          | Productos físicos (sistema legacy)     | FK a duenio, revisor, seguro             |
| `fotos`              | Fotos de productos (legacy)            | FK a producto, foto (bytea)              |
| `fotos_adicionales`  | Fotos con URL (sistema nuevo)          | FK a producto, foto_url                  |
| `seguros`            | Pólizas de seguro                      | nroPoliza (PK), compania, importe        |

### Tablas principales — Operación

| Tabla                  | Propósito                              | Claves                                   |
| ---------------------- | -------------------------------------- | ---------------------------------------- |
| `asistentes`           | Participantes en subastas              | FK a clientes + subastas, numeroPostor  |
| `sesiones_subasta`     | Sesiones activas de subasta            | FK a subasta + cliente, estado (activa/finalizada) |
| `pujos`                | Ofertas/pujas realizadas               | FK a asistente + item, importe, ganador  |
| `puja_idempotency_keys`| Idempotencia de pujas                  | FK a cliente + subasta + item, idempotency_key (UNIQUE), estado |
| `registrodesubasta`    | Registro de cierre/venta               | FK a subasta, duenio, producto, cliente, importe, comision |

### Tablas principales — Pagos y Finanzas

| Tabla                | Propósito                              | Claves                                   |
| -------------------- | -------------------------------------- | ---------------------------------------- |
| `medios_pago`        | Medios de pago del usuario             | FK a clientes, tipo, datos_encriptados, estado_verificacion, moneda, limite_reservado |
| `pagos`              | Pagos de subastas                      | FK a subasta + cliente, total_pujado, comision, costo_envio, total_final, estado, modo_entrega |
| `multas`             | Multas por impago                      | FK a cliente, importe, estado, fecha_limite, medio_pago_id |

### Tablas principales — Comunicación y Seguridad

| Tabla                  | Propósito                              | Claves                                   |
| ---------------------- | -------------------------------------- | ---------------------------------------- |
| `notificaciones`       | Notificaciones push/in-app             | FK a persona, tipo (pago/subasta/sistema), mensaje, leida |
| `blacklisted_tokens`   | Tokens JWT revocados (logout)          | jti (PK), expires_at                     |
| `articulos`            | Artículos consignados (nuevo sistema)  | FK a duenio, estado, fotos[], documentacion_origen[], seguro_poliza FK |

### Relaciones clave

```
personas ──┬── personas_adicionales (email, password)
           ├── clientes ── clientes_adicionales (estado_registro)
           │     ├── asistentes (N a N con subastas)
           │     ├── sesiones_subasta
           │     ├── medios_pago
           │     ├── pagos
           │     └── multas
           ├── duenios
           │     ├── productos ── fotos, itemscatalogo
           │     └── articulos ── seguros
           ├── empleados
           └── subastadores

subastas ──┬── catalogos ── itemscatalogo ── pujos ── puja_idempotency_keys
           ├── asistentes
           ├── sesiones_subasta
           ├── registrodesubasta
           └── pagos

articulos ── seguros ── productos (al aceptar tasación)
```

---

## Endpoints de la API

### Autenticación (`/auth`)
| Método | Ruta                        | Estado       | Descripción                        |
| ------ | --------------------------- | ------------ | ---------------------------------- |
| POST   | `/auth/registro/paso1`      | Implementado | Registro paso 1 (datos + fotos DNI a Supabase) |
| POST   | `/auth/registro/paso2`      | Implementado | Registro paso 2 (token + password + medio de pago opcional) |
| POST   | `/auth/login`               | Implementado | Login con documento + password, retorna JWT |
| POST   | `/auth/logout`              | Implementado | Logout, blacklistea el JWT         |
| POST   | `/auth/verify-email`        | Implementado | Verificar email con token de registración |
| POST   | `/auth/forgot-password`     | Implementado | Solicitar reset de password (envía token por email) |
| POST   | `/auth/reset-password`      | Implementado | Confirmar reset de password con token |

### Perfil (`/usuarios/me`)
| Método | Ruta                              | Estado       | Descripción              |
| ------ | --------------------------------- | ------------ | ------------------------ |
| GET    | `/usuarios/me`                    | Implementado | Obtener perfil propio (persona + cliente + adicionales) |
| PATCH  | `/usuarios/me`                    | Implementado | Actualizar perfil (nombre, apellido, dirección, teléfono, foto) |
| DELETE | `/usuarios/me/foto`               | Implementado | Eliminar foto de perfil |
| GET    | `/usuarios/me/medios-pago`        | Implementado | Listar medios de pago con estado de verificación |
| POST   | `/usuarios/me/medios-pago`        | Implementado | Agregar medio de pago (tarjeta, cuenta bancaria, cheque) |
| PATCH  | `/usuarios/me/medios-pago/{id}`   | Implementado | Actualizar medio de pago (límite, cuenta receptora) |
| DELETE | `/usuarios/me/medios-pago/{id}`   | Implementado | Eliminar medio de pago   |
| GET    | `/usuarios/me/metricas`           | Implementado | Métricas: subastas participadas, ganadas, % éxito, montos |
| GET    | `/usuarios/me/multas`             | Implementado | Listar multas (procesa vencimientos automáticamente) |
| POST   | `/usuarios/me/multas/pagar`       | Implementado | Pagar una multa con medio de pago validado |

### Subastas (`/subastas`)
| Método | Ruta                                       | Estado       | Descripción                      |
| ------ | ------------------------------------------ | ------------ | -------------------------------- |
| GET    | `/subastas/publicas`                       | Implementado | Listar subastas públicas (sin auth, catálogo sin precios) |
| GET    | `/subastas/publicas/{id}`                  | Implementado | Detalle subasta pública          |
| GET    | `/subastas`                                | Implementado | Listar subastas (autenticado, con filtro por categoría) |
| GET    | `/subastas/{id}`                           | Implementado | Detalle con catálogo y precios (requiere categoría suficiente) |
| POST   | `/subastas/{id}/join`                      | Implementado | Unirse a subasta (valida categoría, medio de pago, sesión única) |
| DELETE | `/subastas/{id}/join`                      | Implementado | Salir de subasta                 |
| GET    | `/subastas/{id}/stream`                    | Implementado | SSE en tiempo real (eventos: puja, cierre, keepalive 30s) |
| GET    | `/subastas/{id}/historial`                 | Implementado | Historial de pujas de la subasta |
| GET    | `/subastas/{id}/pagos`                     | Implementado | Resumen de pago del usuario (total, comisión, envío, estado) |
| POST   | `/subastas/{id}/pagos`                     | Implementado | Confirmar pago (medio de pago, modo entrega, seguro) |
| POST   | `/subastas/{id}/cerrar`                    | Implementado | Cerrar subasta (admin): marca ganadores, genera pagos, multas |
| POST   | `/subastas/{id}/items/{itemId}/pujar`      | Implementado | Realizar una puja con validación de límites 1%-20% y garantías |

### Artículos (`/articulos`)
| Método | Ruta                                       | Estado       | Descripción                         |
| ------ | ------------------------------------------ | ------------ | ----------------------------------- |
| POST   | `/articulos`                               | Implementado | Publicar artículo para consignación (min 6 fotos, declaraciones legales) |
| GET    | `/articulos/mis-publicaciones`             | Implementado | Listar artículos del usuario con estado, tasación, seguro, subasta asignada |
| GET    | `/articulos/{id}`                          | Implementado | Detalle de artículo (solo el dueño o admin) |
| POST   | `/articulos/{id}/aceptar-tasacion`         | Implementado | Aceptar/rechazar tasación. Si acepta: crea póliza en `seguros` y registro en `productos` automáticamente |
| POST   | `/articulos/{id}/seguro/aumentar`          | Implementado | Solicitar aumento de cobertura de seguro |

### Notificaciones (`/usuarios/me/notificaciones`)
| Método | Ruta                                       | Estado       | Descripción               |
| ------ | ------------------------------------------ | ------------ | ------------------------- |
| GET    | `/usuarios/me/notificaciones`              | Implementado | Listar notificaciones (pago, subasta, sistema) |
| POST   | `/usuarios/me/notificaciones/{id}/leer`    | Implementado | Marcar como leída         |

### Administración (`/admin`)
| Método | Ruta                                          | Estado       | Descripción                  |
| ------ | --------------------------------------------- | ------------ | ---------------------------- |
| GET    | `/admin/usuarios/pendientes`                  | Implementado | Listar usuarios con registro pendiente |
| GET    | `/admin/usuarios`                             | Implementado | Listar todos los usuarios |
| POST   | `/admin/usuarios/{id}/verificar`              | Implementado | Aprobar/rechazar usuario (asigna categoría, envía email) |
| PATCH  | `/admin/usuarios/{id}/categoria`              | Implementado | Modificar categoría del usuario |
| GET    | `/admin/articulos/pendientes`                 | Implementado | Listar artículos pendientes de evaluación |
| POST   | `/admin/articulos/{id}/evaluar`               | Implementado | Evaluar artículo (aprobar con precio base y comisión, o rechazar) |
| GET    | `/admin/articulos/aprobados-no-catalogados`   | Implementado | Listar artículos aprobados listos para catalogar |
| GET    | `/admin/medios-pago/pendientes`               | Implementado | Listar medios de pago pendientes de verificación |
| POST   | `/admin/medios-pago/{id}/verificar`           | Implementado | Validar/rechazar medio de pago |
| POST   | `/admin/subastas`                             | Implementado | Crear subasta (fecha >10 días, categoría, moneda, subastador) |
| POST   | `/admin/subastas/{id}/catalogo/items`         | Implementado | Agregar item al catálogo con precio base y comisión |
| GET    | `/admin/subastadores`                         | Implementado | Listar subastadores con nombre y matrícula |
| POST   | `/admin/pagos/procesar-vencimientos`          | Implementado | Procesar pagos vencidos y generar multas/bloqueos |

### Uploads (`/uploads`)
| Método | Ruta              | Estado       | Descripción                          |
| ------ | ----------------- | ------------ | ------------------------------------ |
| POST   | `/uploads/presign`| Implementado | Generar URL firmada para upload a Supabase Storage |

### Países (`/paises`)
| Método | Ruta     | Estado       | Descripción        |
| ------ | -------- | ------------ | ------------------ |
| GET    | `/paises`| Implementado | Listar países desde DB |

### Health
| Método | Ruta | Estado       | Descripción              |
| ------ | ---- | ------------ | ------------------------ |
| GET    | `/`  | Implementado | Health check: `{"message": "Hello, Snickers!"}` |

---

## Autenticación y Seguridad

### Flujo de login (implementado)

1. El usuario envía `documento` + `password`
2. Se busca en `personas` + `clientes` (JOIN)
3. Validaciones: usuario no bloqueado, estadoRegistro = aprobado, admitido = si
4. Se verifica password con bcrypt
5. Se genera JWT con claims: `usuarioId`, `categoria`, `admitido`, `jti`, `exp`
6. Se retorna `access_token` + datos del usuario

### Flujo de logout

1. Se extrae el `jti` del token
2. Se inserta en `blacklisted_tokens`
3. El middleware `is_token_blacklisted()` verifica cada request

### Seguridad

- Passwords hasheados con bcrypt
- JWT firmado con `secret_key` configurable
- Blacklist de tokens en DB para logout
- TTL de access token configurable (default 30 min)
- Las rutas protegidas usan `Depends(get_current_user)`

---

## Servicios y Repositorios

### Servicios

| Archivo                  | Clase                  | Estado       | Descripción                                    |
| ------------------------ | ---------------------- | ------------ | ---------------------------------------------- |
| `auth_service.py`        | `AuthService`          | Implementado | login, logout, token blacklist, registro paso 2 |
| `usuario_service.py`     | `UsuarioService`       | Implementado | Perfil CRUD, medios de pago CRUD, métricas, multas |
| `subasta_service.py`     | `SubastaService`       | Implementado | Listados, join/leave, pujas con límites, cierre, vencimientos, pagos |
| `articulo_service.py`    | `ArticuloService`      | Implementado | Publicación con fotos, tasación, seguro, creación automática de póliza |
| `notificacion_service.py`| `NotificacionService`  | Implementado | Listar y marcar notificaciones por usuario |
| `admin_service.py`       | `AdminService`         | Implementado | Verificación de usuarios, artículos, medios de pago, subastas |
| `email_service.py`       | `EmailService`         | Implementado | Envío de emails (Resend / SendGrid / SMTP configurable) |
| `streamer.py`            | `SubastaStreamer`      | Implementado | SSE singleton: subscribe, unsubscribe, broadcast (puja/cierre/keepalive) |
| `storage_service.py`     | `StorageService`       | Implementado | Upload de archivos a Supabase Storage con presigned URLs |

### Repositorios

| Archivo                  | Clase                   | Estado       | Descripción                                    |
| ------------------------ | ----------------------- | ------------ | ---------------------------------------------- |
| `usuario_repo.py`        | `UsuarioRepository`     | Implementado | Usuarios: get, update, registro, verificación, métricas |
| `subasta_repo.py`        | `SubastaRepository`     | Implementado | Subastas: CRUD, asistentes, catálogo, cierre |
| `articulo_repo.py`       | `ArticuloRepository`    | Implementado | Artículos: publicación, evaluación, tasación, seguro |
| `puja_repo.py`           | `PujaRepository`        | Implementado | Pujas: insert, historial, idempotencia, ganadores |
| `notificacion_repo.py`   | `NotificacionRepository`| Implementado | Notificaciones: insertar, listar, marcar leída |

---

## Configuración

### Variables de entorno (`.env`)

| Variable                     | Descripción                              |
| ---------------------------- | ---------------------------------------- |
| `DATABASE_URL`               | URL de conexión a PostgreSQL (Supabase)  |
| `SUPABASE_URL`               | URL del proyecto Supabase                |
| `SUPABASE_SERVICE_ROLE_KEY`  | Service role key de Supabase             |
| `SECRET_KEY`                 | Clave para firmar JWT (default en código)|
| `ACCESS_TOKEN_EXPIRE_MINUTES`| TTL del token (default: 30)              |

### Configuración Pydantic (`app/config.py`)

```python
class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
```

---

## Cómo ejecutar

### Local

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar .env con credenciales de Supabase
#    DATABASE_URL=postgresql://...
#    SUPABASE_URL=https://...
#    SUPABASE_SERVICE_ROLE_KEY=eyJ...

# 4. Iniciar servidor de desarrollo
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Acceder a la API

| Recurso    | URL                             |
| ---------- | ------------------------------- |
| App        | http://127.0.0.1:8000           |
| Swagger UI | http://127.0.0.1:8000/docs      |
| ReDoc      | http://127.0.0.1:8000/redoc     |

---

## Despliegue con Docker

```bash
docker build -t backend-da1 .
docker run -p 8000:8000 --env-file .env backend-da1
```

El `Dockerfile` usa `python:3.12-slim` e instala el driver ODBC 18 para SQL Server (no utilizado actualmente — la app usa psycopg para PostgreSQL).

---

## Testing

El proyecto cuenta con una **suite de tests automatizados** en el directorio `tests/`, ejecutables con `pytest`:

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests con cobertura
pytest --cov=app tests/
```

Los tests validan flujos críticos de negocio:
- **Procesamiento de vencimientos**: pagos expirados, generación de multas del 10%, bloqueo de usuarios.
- **Límites de puja**: validación de mínimo (1% base) y máximo (20% base) para categorías no premium, sin límites para oro/platino.
- **Idempotencia**: pujas duplicadas con misma `Idempotency-Key` retornan resultado cacheado; parámetros distintos devuelven conflicto.
- **Garantías financieras**: exposición total no puede exceder los límites de los medios de pago validados.

### Smoke tests manuales

```bash
# Contra servidor local
bash scripts/smoke_local.sh

# Contra servidor en Render
bash scripts/smoke_online.sh
```

Los smoke tests verifican salud del servidor, login, listado de subastas y endpoints clave.
