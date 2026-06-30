-- Agrega tope máximo personalizado por asistente (usuario-subasta).
-- Cuando es NULL se aplica el 20% predefinido.
-- Valor almacenado como fracción decimal (ej: 0.35 = 35%).
ALTER TABLE public.asistentes
  ADD COLUMN tope_maximo numeric(5,4) DEFAULT NULL
    CHECK (tope_maximo > 0 AND tope_maximo <= 1);