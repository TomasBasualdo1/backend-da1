# 09 · Context Maintenance

Registro de qué documentación previa existía y qué se hizo con ella al construir esta carpeta `context/`.

## Documentación encontrada (antes)

| Ubicación | Contenido | Estado |
|-----------|-----------|--------|
| `app/context/` | 4 stubs SDD: `project-overview.md`, `architecture-context.md`, `code-standards.md`, `ai-workflow-rules.md` (cortos, con `[cite: N]` de la consigna; mezclaban front y back) | Redundante / desubicado (dentro de `app/`) |
| `DOCUMENTATION.md` (raíz) | Doc técnica extensa (tech stack, estructura, endpoints, DB, deploy) en español, buena calidad | Útil, complementaria |
| `docs/` | `Swagger_v5.YAML` (contrato), SQL histórico, `run_migration.py` | Útil (fuente de verdad) |
| `db/` | Esquema PostgreSQL actual + seeds demo + rollback | Útil (fuente de verdad) |
| `plans/login-implementation.md` | Nota de planificación de login | Histórico |
| `context/TPO_DAI_1C2026.md` | **Consigna oficial del TPO** (agregada por el equipo) | Conservada como fuente de verdad del dominio |

## Decisiones tomadas

1. **`app/context/` → archivado.** Los 4 stubs se movieron a `context/_legacy/` (con `git mv`). Su contenido fue **absorbido y ampliado** en los nuevos archivos numerados (overview, architecture, code-conventions, ai-workflow). Se eliminó la carpeta `app/context/` vacía. Motivo: vivían dentro de `app/` (lugar incorrecto), eran genéricos y mezclaban contexto de ambos repos.
2. **`DOCUMENTATION.md` (raíz) → conservado en su lugar.** No se movió ni borró: sigue siendo válido como referencia extendida. Esta carpeta lo enlaza y, ante conflicto, prioriza lo verificado en código.
3. **`docs/` y `db/` → intactos.** Son fuentes de verdad (contrato y esquema). `context/` los referencia, no los duplica.
4. **`plans/` → intacto.** Histórico; no aporta a la operación diaria pero no estorba.
5. **Nada se borró por redundancia sin antes integrarlo.** Lo legado quedó en `context/_legacy/` por trazabilidad.

## Estructura resultante de `context/`

```
context/
├── README.md                 # índice + orden de lectura
├── 00_OVERVIEW.md
├── 01_ARCHITECTURE.md
├── 02_SETUP_AND_RUN.md
├── 03_CODE_CONVENTIONS.md
├── 04_AI_WORKFLOW.md
├── 05_NEW_FILES_GUIDE.md
├── 06_TESTING_AND_VALIDATION.md
├── 07_DOMAIN_NOTES.md
├── 08_PENDING_CONTEXT.md
├── 09_CONTEXT_MAINTENANCE.md  # este archivo
├── 10_API_REFERENCE.md
├── 11_DATABASE.md
├── 12_INTEGRATION.md          # relación con frontend-da1
├── 13_SECURITY.md             # secretos, hallazgos de seguridad, user de prueba
├── TPO_DAI_1C2026.md          # consigna oficial del TPO (fuente de verdad del dominio)
└── _legacy/                   # stubs SDD viejos de app/context (archivados)
```

## Cómo mantener esta carpeta

- Al cambiar endpoints → actualizar `10_API_REFERENCE.md` (y el Swagger).
- Al cambiar esquema → actualizar `11_DATABASE.md` (y el `.sql` en `db/`).
- Al cambiar reglas de negocio → `07_DOMAIN_NOTES.md`.
- Al resolver un pendiente → moverlo de `08_PENDING_CONTEXT.md` a la doc que corresponda.
- `_legacy/` puede borrarse cuando el equipo confirme que no se necesita su trazabilidad.
