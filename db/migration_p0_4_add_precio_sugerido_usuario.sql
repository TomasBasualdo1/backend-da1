-- Agrega columna para el precio sugerido por el usuario al consignar un articulo.
-- Es independiente del precio_base_propuesto que define el admin durante la evaluacion.
ALTER TABLE public.articulos
ADD COLUMN IF NOT EXISTS precio_sugerido_usuario numeric;
