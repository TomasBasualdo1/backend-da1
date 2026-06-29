-- Script para eliminar todas las subastas de la base de datos sin borrar los productos.
-- Desvincula los productos de sus catálogos eliminando los registros de itemscatalogo,
-- y luego limpia de forma en cascada ordenada todas las relaciones de subastas.
--
-- Uso local:
--   DATABASE_URL="postgresql://usuario:password@host:puerto/db" psql "$DATABASE_URL" -f db/clear_all_subastas.sql
--
-- Uso con Supabase:
--   SUPABASE_DB_URL="postgresql://postgres.PROJECT_REF:password@aws-...pooler.supabase.com:6543/postgres" \
--     psql "$SUPABASE_DB_URL" -f db/clear_all_subastas.sql

BEGIN;

-- 1. Eliminar llaves de idempotencia de pujas
DELETE FROM public.puja_idempotency_keys;

-- 2. Eliminar las pujas (bids) asociadas a los asistentes y los ítems de catálogo
DELETE FROM public.pujos;

-- 3. Eliminar los asistentes de las subastas
DELETE FROM public.asistentes;

-- 4. Eliminar el registro histórico de subastas
DELETE FROM public.registrodesubasta;

-- 5. Eliminar los pagos asociados a subastas
DELETE FROM public.pagos;

-- 6. Eliminar las sesiones de subasta activas o finalizadas
DELETE FROM public.sesiones_subasta;

-- 7. Eliminar los ítems de catálogo (esto desvincula los productos sin borrarlos)
DELETE FROM public.itemscatalogo;

-- 8. Eliminar los catálogos en sí
DELETE FROM public.catalogos;

-- 9. Por último, eliminar todas las subastas
DELETE FROM public.subastas;

COMMIT;
