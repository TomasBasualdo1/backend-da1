# 08 · Pending Context

Cosas **no confirmables** solo leyendo el repo, riesgos y deuda. Resolver con el equipo o verificando contra el entorno real.

## PENDIENTE DE CONFIRMAR

- **Sentry**: `sentry-sdk` está en `requirements.txt` pero no se vio `sentry_sdk.init()`. ¿Está activo? ¿Dónde se configura el DSN?
- **`/auth/verify-email`**: endpoint definido pero con cuerpo `pass` (no hace nada). ¿La verificación de email se considera implícita al aprobar el registro? El flujo real de "verificación por email" no está cerrado.
- **Creación automática de multas (10%) y bloqueo: código muerto.** Existen `SubastaRepository.generar_multa` y `bloquear_usuario`, pero **ningún flujo los llama**. No hay disparador de "el ganador no pagó en 72hs → multa + bloqueo". ¿Falta un job/scheduler que venza pagos y aplique la multa? ¿O acción manual del admin? Hoy simplemente no ocurre.
- **Cierre de subasta automático**: `/subastas/{id}/cerrar` es manual. ¿Hay (o debería haber) un scheduler que cierre por fecha/hora? No se detectó cron/worker.
- **`pagos.costo_envio` / `modoEntrega = envio`**: el costo de envío existe en el modelo pero PENDIENTE confirmar dónde/cómo se calcula.
- **Esquema SQL vs BD real**: el `.sql` es snapshot "for context only". Confirmar contra Supabase antes de depender de columnas nuevas.
- **Migraciones**: `docs/run_migration.py` existe; PENDIENTE confirmar si es el mecanismo oficial y cómo se aplican cambios de esquema en prod.
- **Multiworker / escalado**: SSE usa estado en memoria. Si Render corre >1 worker, el broadcast se rompe. Confirmar config de despliegue (workers=1?).

## Tareas pendientes conocidas del equipo (de Notion)

Confirmadas por el equipo, relevantes al backend:

- **Desacoplar el registro (CONFIRMADO, prioridad).** Hoy `registro_paso1` auto-aprueba (`aprobar_registro`). Debe NO aceptarse automáticamente: un admin tiene que **evaluar la solicitud** y, según la decisión, enviar mail de éxito (con el código/token para completar el registro) o mail de rechazo. La lógica de aprobación debe **sacarse de `/auth/registro/paso1`** y quedar solo en el flujo admin (`/admin/usuarios/{id}/verificar`, que ya envía esos emails).
- **Carga / creación de subastas**: falta el flujo operativo para crear subastas y cargar su catálogo (los endpoints `/admin/subastas*` existen pero sin UI ni protección admin correcta).
- **Validaciones de creación de artículo (lado contrato/back)**: `fechaCreacion` debe ser una fecha válida y `precioBasePropuesto`/valor estimado solo números. Hoy el front deja escribir cualquier cosa; conviene validar también en backend.

> Ítems ya resueltos (de la misma lista): recuperación de contraseña, seed de subastas demo, separar medio de pago del cambio de password, campo país en registro.

## Reglas de la consigna (TPO) sin implementar / a verificar

Derivadas de [TPO_DAI_1C2026.md](TPO_DAI_1C2026.md), no presentes en el código:

- **Mejora de categoría**: la consigna dice que la diversidad de medios de pago + la actividad mejoran la categoría del usuario. Hoy la categoría solo se fija al aprobar; no hay mecanismo de upgrade.
- **Límite de compra por garantía**: si el usuario dejó un monto como garantía (cheque certificado), sus compras no pueden superarlo (`medios_pago.limite_reservado`). **No se valida** al pujar/pagar.
- **Multa/bloqueo + escalado a justicia**: ver arriba (código muerto). Incluye el bloqueo permanente por incumplimiento.
- **Subasta "colección"** (juntar muchos artículos de un mismo cliente bajo su nombre): no existe.
- **Trazabilidad de envío/seguro**: confirmar que el dueño puede ver depósito (`articulos.ubicacion`) y póliza, y el aumento de póliza (existe `/articulos/{id}/seguro/aumentar`, validar end-to-end).
- **Idempotencia de pujas** (consigna: "no permitir otra puja hasta confirmación"): el `FOR UPDATE` ayuda, pero falta el `Idempotency-Key` / lock del lado cliente-servidor completo.

## Riesgos / deuda técnica detectada

1. **Autorización admin inconsistente** (alto): solo `/admin/articulos/{id}/evaluar` llama `_require_admin`. `verificar usuarios`, `verificar medios-pago`, `crear subasta` y `agregar item al catálogo` quedan accesibles a **cualquier usuario autenticado**. `/subastas/{id}/cerrar` tampoco valida admin.
2. **Admin hardcodeado** a `usuarioId == 12`. No escala a múltiples admins; debería ser un rol en BD (`empleados`).
3. **`SECRET_KEY` default inseguro** en `config.py` (`"your-secret-key-change-in-production"`). Confirmar que en prod se setea por env.
4. **CORS totalmente abierto** (`allow_origins=["*"]` + `allow_credentials=True`): combinación no recomendada; acotar orígenes en prod.
5. **SQL inline en routers** (`notificaciones.py`, partes de `usuarios.py`/`auth.py`): rompe la separación por capas. Deuda a migrar a services/repos.
6. **Indentación mixta** (2 vs 4 espacios) en `dependencies.py`, `auth_service.py`.
7. **Idempotency-Key ignorada**: doble-tap de puja podría duplicar ofertas (mitigado en parte por `FOR UPDATE`, no del todo).
8. **`datos_encriptados`**: el medio de pago guarda el dato "tal cual" (no se ve cifrado real); el nombre sugiere cifrado que no está implementado.
9. **Token de reset/verificación**: viaja como `token_email` en `personas_adicionales`; confirmar expiración/uso único.

## Info útil para pedirle al equipo

- Valores reales de `.env` (DB, Supabase, email): **disponibles en Notion** del equipo. NO commitearlos. Ver [13_SECURITY.md](13_SECURITY.md).
- ¿Quiénes son admins reales y cómo se modela? ¿Se planea tabla de roles? (hoy admin = `usuarioId == 12`).
- ¿Está vivo el endpoint SSE en prod? ¿Render con cuántos workers?
- ¿La integración con el "sistema local existente de la empresa" (mencionada en la consigna) está dentro de alcance o es teórica?

## Deudas de documentación

- `DOCUMENTATION.md` (raíz) puede tener detalles que difieran del código actual (es previo). Esta carpeta `context/` prioriza lo verificado en código; ante conflicto, **gana el código**.
- No hay diagrama ER formal; [11_DATABASE.md](11_DATABASE.md) lo describe en texto.
