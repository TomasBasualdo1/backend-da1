-- P0.3 - Idempotencia de pujas
-- Ejecutar una vez antes de desplegar el backend que lee Idempotency-Key.

CREATE TABLE IF NOT EXISTS public.puja_idempotency_keys (
  identificador SERIAL PRIMARY KEY,
  cliente_id integer NOT NULL,
  subasta_id integer NOT NULL,
  item_id integer NOT NULL,
  importe numeric NOT NULL CHECK (importe > 0.01),
  idempotency_key character varying(255) NOT NULL,
  estado character varying NOT NULL DEFAULT 'processing'
    CHECK (estado::text = ANY (ARRAY['processing'::character varying, 'completed'::character varying]::text[])),
  puja_id integer,
  mejor_oferta_actual numeric,
  limite_minimo numeric,
  limite_maximo numeric,
  moneda character varying,
  es_ganadora_parcial boolean,
  created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_puja_idempotency_cliente_key UNIQUE (cliente_id, idempotency_key),
  CONSTRAINT fk_puja_idempotency_cliente FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_puja_idempotency_subasta FOREIGN KEY (subasta_id) REFERENCES public.subastas(identificador),
  CONSTRAINT fk_puja_idempotency_item FOREIGN KEY (item_id) REFERENCES public.itemscatalogo(identificador),
  CONSTRAINT fk_puja_idempotency_puja FOREIGN KEY (puja_id) REFERENCES public.pujos(identificador)
);

CREATE INDEX IF NOT EXISTS idx_puja_idempotency_cliente_key
  ON public.puja_idempotency_keys (cliente_id, idempotency_key);
