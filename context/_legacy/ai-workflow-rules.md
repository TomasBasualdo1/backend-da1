# AI Workflow Rules

1.  **Spec First:** Nunca generar código sin un archivo `spec` asociado aprobado en la carpeta `specs/`.
2.  **Context Loading:** Antes de proponer soluciones, debes leer obligatoriamente `project-overview.md`, `architecture-context.md` y el esquema Swagger.
3.  **No Hallucinations:** Si la API requiere un endpoint específico, respeta exactamente la ruta y el payload definido en el Swagger.
4.  **Small Chunks:** Resolver un solo endpoint o pantalla por iteración.
5.  **Tracker Update:** Al finalizar un `spec`, actualiza el estado en `progress_tracker.md`.
