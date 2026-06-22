# context/ — backend-da1

Documentación contextual del backend del **Sistema de Subastas**. Su objetivo es que cualquier desarrollador o IA pueda entender el repo y trabajar respetando su arquitectura y convenciones **sin redescubrir todo desde cero**.

> Repo: `backend-da1` · API REST en **FastAPI** (Python 3.12) sobre **Supabase/PostgreSQL**.
> Forma parte de un workspace de 2 repos junto a `frontend-da1` (app Expo/React Native). Ver [12_INTEGRATION.md](12_INTEGRATION.md).

## Orden de lectura recomendado

| # | Archivo | Para qué sirve |
|---|---------|----------------|
| 1 | [00_OVERVIEW.md](00_OVERVIEW.md) | Qué es el proyecto, qué problema resuelve, stack. |
| 2 | [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | Capas, flujo de datos, archivos críticos, patrones. |
| 3 | [02_SETUP_AND_RUN.md](02_SETUP_AND_RUN.md) | Cómo instalar, correr, variables de entorno. |
| 4 | [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md) | Dominio: entidades, flujos de negocio, glosario, reglas. |
| 5 | [11_DATABASE.md](11_DATABASE.md) | Tablas, relaciones y mapeo modelo↔BD. |
| 6 | [10_API_REFERENCE.md](10_API_REFERENCE.md) | Endpoints: rutas, métodos, payloads, archivos responsables. |
| 7 | [03_CODE_CONVENTIONS.md](03_CODE_CONVENTIONS.md) | Convenciones de nombres y estilo por capa. |
| 8 | [05_NEW_FILES_GUIDE.md](05_NEW_FILES_GUIDE.md) | Dónde y cómo crear archivos nuevos. |
| 9 | [04_AI_WORKFLOW.md](04_AI_WORKFLOW.md) | Cómo debe trabajar una IA: qué leer, qué no asumir, checklist. |
| 10 | [06_TESTING_AND_VALIDATION.md](06_TESTING_AND_VALIDATION.md) | Tests, validación manual, checklist pre-commit. |
| 11 | [12_INTEGRATION.md](12_INTEGRATION.md) | Cómo se integra con `frontend-da1`. |
| 12 | [13_SECURITY.md](13_SECURITY.md) | Manejo de secretos, hallazgos de seguridad, usuario de prueba. |
| 13 | [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md) | Lo que no se pudo confirmar / riesgos / deuda. |
| 14 | [09_CONTEXT_MAINTENANCE.md](09_CONTEXT_MAINTENANCE.md) | Qué docs viejos había y qué se hizo con ellos. |
| 15 | [14_IMPLEMENTATION_BACKLOG_FINAL.md](14_IMPLEMENTATION_BACKLOG_FINAL.md) | Backlog final priorizado y estado real de implementación. |
| 16 | [15_IMPLEMENTATION_NOTES.md](15_IMPLEMENTATION_NOTES.md) | Notas de implementación de etapas ya cerradas. |
| 17 | [16_P0_4_SSE_LIVE_NOTES.md](16_P0_4_SSE_LIVE_NOTES.md) | Notas de implementación P0.4: SSE/live updates. |
| 18 | [17_P0_5_PAGOS_NOTES.md](17_P0_5_PAGOS_NOTES.md) | Notas de implementación P0.5: cierre, deuda y pago de subasta. |
| 19 | [19_P0_6_MULTAS_VENCIMIENTOS_BLOQUEO_NOTES.md](19_P0_6_MULTAS_VENCIMIENTOS_BLOQUEO_NOTES.md) | Notas de implementación P0.6: multas, vencimientos y bloqueo. |
| 20 | [20_P1_1_AUCTION_LISTINGS_DETAILS_NOTES.md](20_P1_1_AUCTION_LISTINGS_DETAILS_NOTES.md) | Notas P1.1: listados y detalles de subastas. |
| 21 | [20_P1_4_FRONTEND_MULTAS_NOTES.md](20_P1_4_FRONTEND_MULTAS_NOTES.md) | Notas P1.4: pago de multas en frontend. |
| 22 | [21_P1_5_GARANTIA_LIMITE_NOTES.md](21_P1_5_GARANTIA_LIMITE_NOTES.md) | Notas P1.5: límite por garantía / cheque certificado. |
| 23 | [22_P1_6_TESTS_HARDENING_NOTES.md](22_P1_6_TESTS_HARDENING_NOTES.md) | Notas P1.6: estabilización de suite unittest. |
| 24 | [18_DEPLOY_RELEASE_HARDENING.md](18_DEPLOY_RELEASE_HARDENING.md) | Checklist de Render/Supabase/Expo, env vars y smoke tests de entrega. |

## Fuentes de verdad del repo

- **`context/TPO_DAI_1C2026.md`** — **consigna oficial del TPO** (Desarrollo de Aplicaciones I, 1C2026). Requisitos del dominio: es la autoridad final sobre qué debe hacer el sistema.
- `db/Estructura-PostgreSQL-da1-updated.sql` — esquema PostgreSQL real (snapshot).
- `docs/Swagger_v4.YAML` — contrato OpenAPI 3.0 (origen de los modelos Pydantic).
- `DOCUMENTATION.md` (raíz) — documentación técnica extendida previa, todavía válida y complementaria.
- `app/schemas/schemas.py` — modelos Pydantic generados desde el Swagger.

> **Regla de oro:** si algo no se puede confirmar leyendo el código o estas fuentes, está marcado como `PENDIENTE DE CONFIRMAR` en [08_PENDING_CONTEXT.md](08_PENDING_CONTEXT.md). No inventar endpoints, columnas ni reglas.
