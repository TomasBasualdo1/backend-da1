-- =====================================================================
-- Migración: Flujo de consignación con envío e inspección física
-- Idempotente. Compatible con datos preexistentes.
-- Nuevos estados: 'interesado' y 'en_transito' (se reutiliza 'en_inspeccion').
-- =====================================================================

-- 1) Ampliar el CHECK de estado de articulos
ALTER TABLE public.articulos DROP CONSTRAINT IF EXISTS articulos_estado_check;
ALTER TABLE public.articulos ADD CONSTRAINT articulos_estado_check
  CHECK (estado IN (
    'pendiente', 'interesado', 'en_transito', 'en_inspeccion',
    'aprobado', 'rechazado', 'devuelto'
  ));

-- 2) Dirección que el admin indica al usuario para que envíe el bien
ALTER TABLE public.articulos
  ADD COLUMN IF NOT EXISTS direccion_inspeccion character varying;

-- 3) Instrucciones opcionales de envío (remitente, horarios, acuses, etc.)
ALTER TABLE public.articulos
  ADD COLUMN IF NOT EXISTS instrucciones_envio character varying;

-- 4) Acuerdo del usuario: acepta que la devolución del bien es con cargo
ALTER TABLE public.articulos
  ADD COLUMN IF NOT EXISTS acepta_cargo_devolucion boolean DEFAULT false;

-- 5) Monto del cargo de devolución (definido por el admin al rechazar/devolver)
ALTER TABLE public.articulos
  ADD COLUMN IF NOT EXISTS costo_devolucion numeric CHECK (costo_devolucion IS NULL OR costo_devolucion >= 0);

-- 6) Fecha en la que el usuario confirma el envío físico del bien
ALTER TABLE public.articulos
  ADD COLUMN IF NOT EXISTS fecha_envio_fisico timestamp with time zone;