-- Remover la restricción de antelación mínima en la fecha de la subasta
-- Antes: subastas.fecha tenía un CHECK (fecha > CURRENT_DATE + '10 days')
-- que impedía crear subastas con menos de 10 días de antelación.
-- Ahora: se puede crear una subasta para cualquier fecha, sin restricción.
--
-- El CHECK es anónimo en la BD, por lo que lo buscamos y lo droppeamos
-- dinámicamente (su nombre autogenerado suele ser 'subastas_fecha_check').
-- Ejecutar una vez en Supabase/PostgreSQL antes (o junto) al deploy del backend.

DO $$
DECLARE
  cons_name text;
BEGIN
  SELECT con.conname
    INTO cons_name
  FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid
  JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
  WHERE nsp.nspname = 'public'
    AND rel.relname = 'subastas'
    AND con.contype = 'c'
    AND pg_get_constraintdef(con.oid) ILIKE '%fecha%CURRENT_DATE%';

  IF cons_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.subastas DROP CONSTRAINT %I', cons_name);
    RAISE NOTICE 'Constraint % eliminado de public.subastas.', cons_name;
  ELSE
    RAISE NOTICE 'No se encontró CHECK de antelación en public.subastas (ya estaba removido).';
  END IF;
END $$;
