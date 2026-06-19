# 00 · Overview

## Qué es

API REST del **Sistema de Subastas**: backend de una plataforma donde usuarios verificados participan online en subastas dinámicas ascendentes y consignan (proponen) artículos propios para ser subastados por la empresa.

> **Contexto académico**: es el TPO (Trabajo Práctico Obligatorio) de la materia **Desarrollo de Aplicaciones I**, 1º cuatrimestre 2026. La consigna oficial completa está en **[TPO_DAI_1C2026.md](TPO_DAI_1C2026.md)** (fuente de verdad del dominio). Se evalúa en **3 entregas**: (1) maquetado/wireframes + diseño del API (Swagger); (2) back y front al 50% con ≥1 circuito integrado; (3) app 100% funcional, backend accesible online y front instalable en dispositivo. Exige **trazabilidad**: lo entregado debe coincidir con lo diseñado.

Es el componente servidor de un sistema de 2 repos:
- **`backend-da1`** (este repo) — FastAPI + PostgreSQL/Supabase.
- **`frontend-da1`** — app móvil Expo / React Native que consume esta API.

Título de la app FastAPI: `API Sistema de Subastas` (`main.py`, version `1.2.0`).

- **Repo**: https://github.com/TomasBasualdo1/backend-da1
- **Deploy**: `https://backend-da1.onrender.com` (Render). Está **vivo**; se corre local solo para desarrollar/testear endpoints.

## Qué problema resuelve

La empresa hace remates presenciales y necesita que postores participen **online**, consulten catálogos, pujen en tiempo real, paguen lo ganado, y puedan **consignar** artículos propios para futuras subastas. El backend además debe integrarse conceptualmente con el sistema local existente de la empresa (subastas, dueños, postores, ofertas, martilleros).

## Stack principal

| Categoría | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12 |
| Framework | FastAPI 0.136.x |
| Servidor ASGI | Uvicorn |
| Base de datos | PostgreSQL (Supabase) vía **psycopg 3** (SQL crudo, sin ORM) |
| Auth | JWT (`python-jose`, HS256) + `bcrypt` |
| Validación | Pydantic 2 / pydantic-settings |
| Storage | Supabase Storage (subida vía `httpx`) |
| Email | SMTP / Resend / SendGrid (configurable) |
| Tiempo real | Server-Sent Events (SSE) en memoria |
| Deploy | Docker → Render |

## Partes importantes del repo

```
backend-da1/
├── main.py                 # Entry point: crea FastAPI, CORS, monta router
├── app/
│   ├── config.py           # Settings (pydantic-settings, lee .env)
│   ├── dependencies.py     # get_db, get_current_user (JWT)
│   ├── core/               # database.py (conexión), security.py (JWT/bcrypt)
│   ├── api/                # Routers FastAPI (capa "controller")
│   ├── services/           # Lógica de negocio
│   ├── repositories/       # Acceso a datos (SQL crudo con psycopg)
│   └── schemas/schemas.py  # Modelos Pydantic (generados desde Swagger)
├── db/                     # Esquema SQL real + seeds demo + rollback
├── docs/                   # Swagger_v4.YAML + SQL histórico + run_migration
├── tests/                  # Tests unittest (mockean la DB)
├── plans/                  # Notas de planificación previas
├── Dockerfile              # Imagen para Render
└── DOCUMENTATION.md        # Doc técnica extendida (complementaria)
```

## Relación con el otro repo

`frontend-da1` consume esta API por HTTP (REST) con JWT Bearer. El contrato lo define `docs/Swagger_v4.YAML`, del cual se generaron tanto los modelos Pydantic del backend como los tipos TypeScript del frontend. Detalle en [12_INTEGRATION.md](12_INTEGRATION.md).

> **Nota importante:** el endpoint de tiempo real (SSE `/subastas/{id}/stream`) existe en el backend pero **el frontend todavía no lo consume**. Ver [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md).
