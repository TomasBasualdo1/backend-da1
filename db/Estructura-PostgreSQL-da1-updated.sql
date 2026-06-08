-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.paises (
  numero integer NOT NULL,
  nombre character varying NOT NULL,
  nombrecorto character varying,
  capital character varying NOT NULL,
  nacionalidad character varying NOT NULL,
  idiomas character varying NOT NULL,
  CONSTRAINT paises_pkey PRIMARY KEY (numero)
);
CREATE TABLE public.personas (
  identificador integer NOT NULL DEFAULT nextval('personas_identificador_seq'::regclass),
  documento character varying NOT NULL,
  nombre character varying NOT NULL,
  direccion character varying,
  estado character varying CHECK (estado::text = ANY (ARRAY['activo'::character varying, 'inactivo'::character varying, 'incativo'::character varying]::text[])),
  foto bytea,
  CONSTRAINT personas_pkey PRIMARY KEY (identificador)
);
CREATE TABLE public.empleados (
  identificador integer NOT NULL,
  cargo character varying,
  sector integer,
  CONSTRAINT empleados_pkey PRIMARY KEY (identificador)
);
CREATE TABLE public.sectores (
  identificador integer NOT NULL DEFAULT nextval('sectores_identificador_seq'::regclass),
  nombresector character varying NOT NULL,
  codigosector character varying,
  responsablesector integer,
  CONSTRAINT sectores_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_sectores_empleados FOREIGN KEY (responsablesector) REFERENCES public.empleados(identificador)
);
CREATE TABLE public.seguros (
  nropoliza character varying NOT NULL,
  compania character varying NOT NULL,
  polizacombinada character varying CHECK (polizacombinada::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  importe numeric NOT NULL CHECK (importe > 0::numeric),
  CONSTRAINT seguros_pkey PRIMARY KEY (nropoliza)
);
CREATE TABLE public.clientes (
  identificador integer NOT NULL,
  numeropais integer,
  admitido character varying CHECK (admitido::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  categoria character varying CHECK (categoria::text = ANY (ARRAY['comun'::character varying, 'especial'::character varying, 'plata'::character varying, 'oro'::character varying, 'platino'::character varying]::text[])),
  verificador integer NOT NULL,
  CONSTRAINT clientes_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_clientes_paises FOREIGN KEY (numeropais) REFERENCES public.paises(numero),
  CONSTRAINT fk_clientes_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador),
  CONSTRAINT fk_clientes_empleados FOREIGN KEY (verificador) REFERENCES public.empleados(identificador)
);
CREATE TABLE public.duenios (
  identificador integer NOT NULL,
  numeropais integer,
  verificacionfinanciera character varying CHECK (verificacionfinanciera::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  verificacionjudicial character varying CHECK (verificacionjudicial::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  calificacionriesgo integer CHECK (calificacionriesgo = ANY (ARRAY[1, 2, 3, 4, 5, 6])),
  verificador integer NOT NULL,
  CONSTRAINT duenios_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_duenios_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador),
  CONSTRAINT fk_duenios_empleados FOREIGN KEY (verificador) REFERENCES public.empleados(identificador)
);
CREATE TABLE public.subastadores (
  identificador integer NOT NULL,
  matricula character varying,
  region character varying,
  CONSTRAINT subastadores_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_subastadores_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador)
);
CREATE TABLE public.subastas (
  identificador integer NOT NULL DEFAULT nextval('subastas_identificador_seq'::regclass),
  fecha date CHECK (fecha > (CURRENT_DATE + '10 days'::interval)::date),
  hora time without time zone NOT NULL,
  estado character varying CHECK (estado::text = ANY (ARRAY['abierta'::character varying, 'cerrada'::character varying, 'carrada'::character varying]::text[])),
  subastador integer,
  ubicacion character varying,
  capacidadasistentes integer,
  tienedeposito character varying CHECK (tienedeposito::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  seguridadpropia character varying CHECK (seguridadpropia::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  categoria character varying CHECK (categoria::text = ANY (ARRAY['comun'::character varying, 'especial'::character varying, 'plata'::character varying, 'oro'::character varying, 'platino'::character varying]::text[])),
  CONSTRAINT subastas_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_subastas_subastadores FOREIGN KEY (subastador) REFERENCES public.subastadores(identificador)
);
CREATE TABLE public.productos (
  identificador integer NOT NULL DEFAULT nextval('productos_identificador_seq'::regclass),
  fecha date,
  disponible character varying CHECK (disponible::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  descripcioncatalogo character varying DEFAULT 'No Posee'::character varying,
  descripcioncompleta character varying NOT NULL,
  revisor integer NOT NULL,
  duenio integer NOT NULL,
  seguro character varying,
  CONSTRAINT productos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_productos_empleados FOREIGN KEY (revisor) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_productos_duenios FOREIGN KEY (duenio) REFERENCES public.duenios(identificador)
);
CREATE TABLE public.fotos (
  identificador integer NOT NULL DEFAULT nextval('fotos_identificador_seq'::regclass),
  producto integer NOT NULL,
  foto bytea NOT NULL,
  CONSTRAINT fotos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_fotos_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador)
);
CREATE TABLE public.catalogos (
  identificador integer NOT NULL DEFAULT nextval('catalogos_identificador_seq'::regclass),
  descripcion character varying NOT NULL,
  subasta integer,
  responsable integer NOT NULL,
  CONSTRAINT catalogos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_catalogos_empleados FOREIGN KEY (responsable) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_catalogos_subastas FOREIGN KEY (subasta) REFERENCES public.subastas(identificador)
);
CREATE TABLE public.itemscatalogo (
  identificador integer NOT NULL DEFAULT nextval('itemscatalogo_identificador_seq'::regclass),
  catalogo integer NOT NULL,
  producto integer NOT NULL,
  preciobase numeric NOT NULL CHECK (preciobase > 0.01),
  comision numeric NOT NULL CHECK (comision > 0.01),
  subastado character varying CHECK (subastado::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  CONSTRAINT itemscatalogo_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_itemscatalogo_catalogos FOREIGN KEY (catalogo) REFERENCES public.catalogos(identificador),
  CONSTRAINT fk_itemscatalogo_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador)
);
CREATE TABLE public.asistentes (
  identificador integer NOT NULL DEFAULT nextval('asistentes_identificador_seq'::regclass),
  numeropostor integer NOT NULL,
  cliente integer NOT NULL,
  subasta integer NOT NULL,
  CONSTRAINT asistentes_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_asistentes_clientes FOREIGN KEY (cliente) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_asistentes_subasta FOREIGN KEY (subasta) REFERENCES public.subastas(identificador)
);
CREATE TABLE public.pujos (
  identificador integer NOT NULL DEFAULT nextval('pujos_identificador_seq'::regclass),
  asistente integer NOT NULL,
  item integer NOT NULL,
  importe numeric NOT NULL CHECK (importe > 0.01),
  ganador character varying DEFAULT 'no'::character varying CHECK (ganador::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  CONSTRAINT pujos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_pujos_asistentes FOREIGN KEY (asistente) REFERENCES public.asistentes(identificador),
  CONSTRAINT fk_pujos_itemscatalogo FOREIGN KEY (item) REFERENCES public.itemscatalogo(identificador)
);
CREATE TABLE public.registrodesubasta (
  identificador integer NOT NULL DEFAULT nextval('registrodesubasta_identificador_seq'::regclass),
  subasta integer NOT NULL,
  duenio integer NOT NULL,
  producto integer NOT NULL,
  cliente integer NOT NULL,
  importe numeric NOT NULL CHECK (importe > 0.01),
  comision numeric NOT NULL CHECK (comision > 0.01),
  CONSTRAINT registrodesubasta_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_registrodesubasta_subastas FOREIGN KEY (subasta) REFERENCES public.subastas(identificador),
  CONSTRAINT fk_registrodesubasta_duenios FOREIGN KEY (duenio) REFERENCES public.duenios(identificador),
  CONSTRAINT fk_registrodesubasta_producto FOREIGN KEY (producto) REFERENCES public.productos(identificador),
  CONSTRAINT fk_registrodesubasta_cliente FOREIGN KEY (cliente) REFERENCES public.clientes(identificador)
);
CREATE TABLE public.personas_adicionales (
  identificador integer NOT NULL,
  email character varying UNIQUE,
  password_hash character varying,
  foto_frente character varying,
  foto_dorso character varying,
  telefono character varying,
  token_email character varying,
  foto_url character varying,
  CONSTRAINT personas_adicionales_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_personas_adicionales_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador)
);
CREATE TABLE public.clientes_adicionales (
  identificador integer NOT NULL,
  estado_registro character varying DEFAULT 'pendiente'::character varying CHECK (estado_registro::text = ANY (ARRAY['pendiente'::character varying, 'aprobado'::character varying, 'rechazado'::character varying]::text[])),
  multa_activa boolean DEFAULT false,
  bloqueado boolean DEFAULT false,
  motivo_rechazo character varying,
  CONSTRAINT clientes_adicionales_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_clientes_adicionales_clientes FOREIGN KEY (identificador) REFERENCES public.clientes(identificador)
);
CREATE TABLE public.medios_pago (
  identificador integer NOT NULL DEFAULT nextval('medios_pago_identificador_seq'::regclass),
  cliente_id integer NOT NULL,
  tipo character varying NOT NULL CHECK (tipo::text = ANY (ARRAY['tarjeta_credito'::character varying, 'cuenta_bancaria'::character varying, 'cheque_certificado'::character varying]::text[])),
  datos_encriptados character varying NOT NULL,
  ultimos_digitos character varying NOT NULL,
  estado_verificacion character varying DEFAULT 'pendiente'::character varying CHECK (estado_verificacion::text = ANY (ARRAY['pendiente'::character varying, 'validado'::character varying, 'rechazado'::character varying]::text[])),
  moneda character varying NOT NULL CHECK (moneda::text = ANY (ARRAY['ARS'::character varying, 'USD'::character varying]::text[])),
  limite_reservado numeric DEFAULT 0.00 CHECK (limite_reservado >= 0::numeric),
  pais_banco character varying,
  es_cuenta_receptora boolean DEFAULT false,
  CONSTRAINT medios_pago_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_medios_pago_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador)
);
CREATE TABLE public.multas (
  identificador integer NOT NULL DEFAULT nextval('multas_identificador_seq'::regclass),
  cliente_id integer NOT NULL,
  importe numeric NOT NULL CHECK (importe > 0::numeric),
  estado character varying DEFAULT 'pendiente'::character varying CHECK (estado::text = ANY (ARRAY['pendiente'::character varying, 'pagada'::character varying]::text[])),
  fecha_limite timestamp with time zone NOT NULL,
  motivo character varying,
  medio_pago_id integer,
  CONSTRAINT multas_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_multas_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_multas_medios_pago FOREIGN KEY (medio_pago_id) REFERENCES public.medios_pago(identificador)
);
CREATE TABLE public.notificaciones (
  identificador integer NOT NULL DEFAULT nextval('notificaciones_identificador_seq'::regclass),
  persona_id integer NOT NULL,
  tipo character varying NOT NULL CHECK (tipo::text = ANY (ARRAY['pago'::character varying, 'subasta'::character varying, 'sistema'::character varying]::text[])),
  mensaje character varying NOT NULL,
  fecha_hora timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  leida boolean DEFAULT false,
  CONSTRAINT notificaciones_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_notificaciones_personas FOREIGN KEY (persona_id) REFERENCES public.personas(identificador)
);
CREATE TABLE public.blacklisted_tokens (
  jti character varying NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  CONSTRAINT blacklisted_tokens_pkey PRIMARY KEY (jti)
);
CREATE TABLE public.articulos (
  identificador integer NOT NULL DEFAULT nextval('articulos_identificador_seq'::regclass),
  duenio_id integer NOT NULL,
  descripcion character varying NOT NULL,
  historia character varying,
  artista character varying,
  fecha_creacion date,
  es_propietario boolean DEFAULT true,
  declara_origen_licito boolean DEFAULT true,
  estado character varying DEFAULT 'pendiente'::character varying CHECK (estado::text = ANY (ARRAY['pendiente'::character varying, 'en_inspeccion'::character varying, 'aprobado'::character varying, 'rechazado'::character varying, 'devuelto'::character varying]::text[])),
  motivo_rechazo character varying,
  precio_base_propuesto numeric,
  comision_propuesta numeric,
  tasacion_aceptada boolean,
  fecha_envio timestamp with time zone,
  ubicacion character varying DEFAULT 'Deposito CABA'::character varying,
  seguro_poliza character varying,
  fotos ARRAY,
  documentacion_origen ARRAY,
  CONSTRAINT articulos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_articulos_duenios FOREIGN KEY (duenio_id) REFERENCES public.duenios(identificador),
  CONSTRAINT fk_articulos_seguros FOREIGN KEY (seguro_poliza) REFERENCES public.seguros(nropoliza)
);
CREATE TABLE public.pagos (
  identificador integer NOT NULL DEFAULT nextval('pagos_identificador_seq'::regclass),
  subasta_id integer NOT NULL,
  cliente_id integer NOT NULL,
  total_pujado numeric NOT NULL CHECK (total_pujado >= 0::numeric),
  comision numeric NOT NULL CHECK (comision >= 0::numeric),
  costo_envio numeric DEFAULT 0.00 CHECK (costo_envio >= 0::numeric),
  total_final numeric NOT NULL CHECK (total_final >= 0::numeric),
  moneda character varying NOT NULL CHECK (moneda::text = ANY (ARRAY['ARS'::character varying, 'USD'::character varying]::text[])),
  modo_entrega character varying CHECK (modo_entrega::text = ANY (ARRAY['envio'::character varying, 'retiro'::character varying]::text[])),
  direccion_envio character varying,
  estado character varying DEFAULT 'pendiente'::character varying CHECK (estado::text = ANY (ARRAY['pendiente'::character varying, 'pagado'::character varying, 'vencido'::character varying]::text[])),
  fecha_limite_pago timestamp with time zone NOT NULL,
  medio_pago_id integer,
  acepta_perder_seguro boolean DEFAULT false,
  CONSTRAINT pagos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_pagos_subastas FOREIGN KEY (subasta_id) REFERENCES public.subastas(identificador),
  CONSTRAINT fk_pagos_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_pagos_medios_pago FOREIGN KEY (medio_pago_id) REFERENCES public.medios_pago(identificador)
);
CREATE TABLE public.sesiones_subasta (
  identificador integer NOT NULL DEFAULT nextval('sesiones_subasta_identificador_seq'::regclass),
  subasta_id integer NOT NULL,
  cliente_id integer NOT NULL,
  estado character varying DEFAULT 'activa'::character varying CHECK (estado::text = ANY (ARRAY['activa'::character varying, 'finalizada'::character varying]::text[])),
  fecha_hora_inicio timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT sesiones_subasta_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_sesiones_subasta_subastas FOREIGN KEY (subasta_id) REFERENCES public.subastas(identificador),
  CONSTRAINT fk_sesiones_subasta_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador)
);