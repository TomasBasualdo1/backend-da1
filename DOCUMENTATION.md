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
│   ├── dependencies.py              # Inyección de dependencias (get_db, get_current_user)
│   │
│   ├── api/                         # Controladores (route handlers)
│   │   ├── router.py                # Router principal que agrega todos los sub-routers
│   │   ├── auth.py                  # Registro, login, logout, email verification
│   │   ├── usuarios.py              # Perfil, medios de pago, métricas, multas
│   │   ├── subastas.py              # Subastas públicas, detalle, join, pujas, streaming
│   │   ├── articulos.py             # Publicación, tasación, seguro
│   │   ├── notificaciones.py        # Listar y marcar notificaciones
│   │   ├── admin.py                 # Admin: verificar usuarios, medios de pago, artículos
│   │   ├── uploads.py               # Presigned URLs para upload a Supabase Storage
│   │   └── paises.py                # Listado de países
│   │
│   ├── core/
│   │   ├── database.py              # Conexión a PostgreSQL (psycopg, dict_row)
│   │   └── security.py              # Hashing bcrypt + creación/validación JWT
│   │
│   ├── services/                    # Capa de lógica de negocio
│   │   ├── auth_service.py          # AuthService (login, logout — implementado)
│   │   ├── usuario_service.py       # UsuarioService — stub
│   │   ├── subasta_service.py       # SubastaService — stub
│   │   ├── email_service.py         # EmailService — stub
│   │   └── storage_service.py       # StorageService — stub
│   │
│   ├── repositories/                # Capa de acceso a datos
│   │   ├── usuario_repo.py          # UsuarioRepository — stub
│   │   ├── subasta_repo.py          # SubastaRepository — stub
│   │   ├── articulo_repo.py         # ArticuloRepository — stub
│   │   └── puja_repo.py             # PujaRepository — stub
│   │
│   └── schemas/
│       └── schemas.py               # Modelos Pydantic (~430 líneas)
│
├── db/
│   ├── Estructura-PostgreSQL-da1.sql  # Schema completo (14 tablas)
│   └── Swagger_v5.YAML                # Especificación OpenAPI 3.0
│
├── context/                         # Documentación interna del proyecto
│   ├── project-overview.md
│   ├── architecture-context.md
│   ├── code-standards.md
│   └── ai-workflow-rules.md
│
└── plans/
    └── login-implementation.md      # Plan de implementación del login
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
- **Idempotency-Key** planeado para pujas (evita pujas duplicadas)
- **Locking pesimista** en PostgreSQL planeado para concurrencia en pujas
- **Server-Sent Events (SSE)** planeado para bidding en tiempo real

### Estado de implementación

- **4 endpoints implementados**: login, logout, presign uploads, listar países
- **~30 endpoints restantes**: tienen ruta y DI configurados pero sin lógica (stubs)
- **Services y repositories**: auth_service completo; el resto son stubs vacíos

---

## Base de Datos

**Motor:** PostgreSQL (Supabase)

**Esquema** (`db/Estructura-PostgreSQL-da1.sql`) — 16 tablas:

### Tablas principales

| Tabla                | Propósito                              | Claves                            |
| -------------------- | -------------------------------------- | --------------------------------- |
| `personas`           | Personas físicas (usuarios, empleados, subastadores) | documento, email (único), password_hash |
| `clientes`           | Clientes/usuarios de la plataforma     | FK a personas, estadoRegistro, categoría |
| `duenios`            | Dueños de artículos                    | FK a personas, verificación financiera/judicial |
| `empleados`          | Empleados de la empresa                | FK a personas, cargo, sector      |
| `subastadores`       | Martilleros/subastadores               | FK a personas, matrícula, región  |
| `paises`             | Catálogo de países                     | numero (PK), nombre, nacionalidad |
| `subastas`           | Eventos de subasta                     | fecha, hora, estado, subastador FK |
| `asistentes`         | Participantes en subastas              | FK a clientes + subastas, nroPostor |
| `catalogos`          | Catálogos de subasta                   | FK a subasta + empleado responsable |
| `productos`          | Artículos/productos físicos            | FK a duenio, revisor, seguro      |
| `itemscatalogo`      | Items dentro de un catálogo            | FK a catálogo + producto, precioBase, comisión |
| `pujos`              | Ofertas/pujas                          | FK a asistente + item, importe, ganador |
| `fotos`              | Fotos de productos                     | FK a producto, url                |
| `sectores`           | Sectores/departamentos de la empresa   | responsableSector FK              |
| `registrodesubasta`  | Registro de cierre de subasta          | FK a subasta, duenio, producto, cliente |
| `seguros`            | Pólizas de seguro                      | nroPoliza (PK), compañía, importe |
| `blacklisted_tokens` | Tokens JWT revocados                   | jti (PK), expires_at              |

### Relaciones clave

```
personas ──┬── clientes (rol: comprador/postor)
           ├── duenios (rol: vendedor/consignador)
           ├── empleados (rol: staff interno)
           └── subastadores (rol: martillero)

subastas ──┬── asistentes (N a N con clientes)
           ├── catalogos (1 a N)
           └── registrodesubasta (cierre)

catalogos ── itemscatalogo ── pujos
                               └── asistentes

productos ──┬── fotos
            ├── duenios
            └── seguros
```

---

## Endpoints de la API

### Autenticación (`/auth`)
| Método | Ruta                        | Estado       | Descripción                        |
| ------ | --------------------------- | ------------ | ---------------------------------- |
| POST   | `/auth/registro/paso1`      | Stub         | Registro paso 1 (datos + fotos DNI)|
| POST   | `/auth/registro/paso2`      | Stub         | Registro paso 2 (token + password) |
| POST   | `/auth/login`               | Implementado | Login con documento + password     |
| POST   | `/auth/logout`              | Implementado | Logout, blacklistea el JWT         |
| POST   | `/auth/verify-email`        | Stub         | Verificar email con token          |
| POST   | `/auth/forgot-password`     | Stub         | Solicitar reset de password        |
| POST   | `/auth/reset-password`      | Stub         | Confirmar reset de password        |

### Perfil (`/usuarios/me`)
| Método | Ruta                              | Estado | Descripción              |
| ------ | --------------------------------- | ------ | ------------------------ |
| GET    | `/usuarios/me`                    | Stub   | Obtener perfil propio    |
| PATCH  | `/usuarios/me`                    | Stub   | Actualizar perfil        |
| GET    | `/usuarios/me/medios-pago`        | Stub   | Listar medios de pago    |
| POST   | `/usuarios/me/medios-pago`        | Stub   | Agregar medio de pago    |
| PATCH  | `/usuarios/me/medios-pago/{id}`   | Stub   | Actualizar medio de pago |
| DELETE | `/usuarios/me/medios-pago/{id}`   | Stub   | Eliminar medio de pago   |
| GET    | `/usuarios/me/metricas`           | Stub   | Métricas de participación|
| GET    | `/usuarios/me/multas`             | Stub   | Listar multas            |
| POST   | `/usuarios/me/multas/pagar`       | Stub   | Pagar una multa          |

### Subastas (`/subastas`)
| Método | Ruta                                       | Estado | Descripción                      |
| ------ | ------------------------------------------ | ------ | -------------------------------- |
| GET    | `/subastas/publicas`                       | Stub   | Listar subastas públicas (sin auth) |
| GET    | `/subastas/publicas/{id}`                  | Stub   | Detalle subasta pública          |
| GET    | `/subastas`                                | Stub   | Listar subastas (autenticado)    |
| GET    | `/subastas/{id}`                           | Stub   | Detalle con catálogo             |
| POST   | `/subastas/{id}/join`                      | Stub   | Unirse a subasta                 |
| DELETE | `/subastas/{id}/join`                      | Stub   | Salir de subasta                 |
| GET    | `/subastas/{id}/stream`                    | Stub   | SSE en tiempo real               |
| GET    | `/subastas/{id}/historial`                 | Stub   | Historial de pujas               |
| GET    | `/subastas/{id}/pagos`                     | Stub   | Resumen de pagos                 |
| POST   | `/subastas/{id}/pagos`                     | Stub   | Confirmar pago                   |
| POST   | `/subastas/{id}/cerrar`                    | Stub   | Cerrar subasta (admin)           |
| POST   | `/subastas/{id}/items/{itemId}/pujar`      | Stub   | Realizar una puja                |

### Artículos (`/articulos`)
| Método | Ruta                                       | Estado | Descripción                         |
| ------ | ------------------------------------------ | ------ | ----------------------------------- |
| POST   | `/articulos`                               | Stub   | Publicar artículo para consignación |
| GET    | `/articulos/mis-publicaciones`             | Stub   | Listar artículos del usuario        |
| GET    | `/articulos/{id}`                          | Stub   | Detalle de artículo                 |
| POST   | `/articulos/{id}/aceptar-tasacion`         | Stub   | Aceptar/rechazar tasación           |
| POST   | `/articulos/{id}/seguro/aumentar`          | Stub   | Solicitar aumento de seguro         |

### Notificaciones (`/usuarios/me/notificaciones`)
| Método | Ruta                                       | Estado | Descripción               |
| ------ | ------------------------------------------ | ------ | ------------------------- |
| GET    | `/usuarios/me/notificaciones`              | Stub   | Listar notificaciones     |
| POST   | `/usuarios/me/notificaciones/{id}/leer`    | Stub   | Marcar como leída         |

### Administración (`/admin`)
| Método | Ruta                                       | Estado | Descripción                  |
| ------ | ------------------------------------------ | ------ | ---------------------------- |
| POST   | `/admin/usuarios/{id}/verificar`           | Stub   | Aprobar/rechazar usuario     |
| POST   | `/admin/medios-pago/{id}/verificar`        | Stub   | Verificar medio de pago      |
| POST   | `/admin/articulos/{id}/evaluar`            | Stub   | Evaluar artículo consignado  |
| POST   | `/admin/subastas`                          | Stub   | Crear subasta                |
| POST   | `/admin/subastas/{id}/catalogo/items`      | Stub   | Agregar item al catálogo     |

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

| Archivo              | Clase                | Estado       | Descripción                       |
| -------------------- | -------------------- | ------------ | --------------------------------- |
| `auth_service.py`    | `AuthService`        | Implementado | login, logout, token blacklist    |
| `usuario_service.py` | `UsuarioService`     | Stub         | Perfil, medios de pago, métricas  |
| `subasta_service.py` | `SubastaService`     | Stub         | CRUD subastas, join/leave, pujas  |
| `email_service.py`   | `EmailService`       | Stub         | Envío de emails transaccionales   |
| `storage_service.py` | `StorageService`     | Stub         | Upload de archivos a Supabase     |
| `usuario_repo.py`    | `UsuarioRepository`  | Stub         | Consultas SQL de usuarios         |
| `subasta_repo.py`    | `SubastaRepository`  | Stub         | Consultas SQL de subastas         |
| `articulo_repo.py`   | `ArticuloRepository` | Stub         | Consultas SQL de artículos        |
| `puja_repo.py`       | `PujaRepository`     | Stub         | Consultas SQL de pujas            |

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

Actualmente **no hay infraestructura de tests** (no hay pytest, ni archivos `test_*.py`, ni directorio `tests/`). Es necesario agregar cobertura de tests antes de producción.
