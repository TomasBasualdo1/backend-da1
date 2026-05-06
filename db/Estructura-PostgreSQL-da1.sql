-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.asistentes (
  identificador integer NOT NULL DEFAULT nextval('asistentes_identificador_seq'::regclass),
  numeropostor integer NOT NULL,
  cliente integer NOT NULL,
  subasta integer NOT NULL,
  CONSTRAINT asistentes_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_asistentes_clientes FOREIGN KEY (cliente) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_asistentes_subasta FOREIGN KEY (subasta) REFERENCES public.subastas(identificador)
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
CREATE TABLE public.clientes (
  identificador integer NOT NULL,
  numeropais integer,
  admitido character varying CHECK (admitido::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  categoria character varying CHECK (categoria::text = ANY (ARRAY['comun'::character varying, 'especial'::character varying, 'plata'::character varying, 'oro'::character varying, 'platino'::character varying]::text[])),
  verificador integer NOT NULL,
  estadoRegistro character varying DEFAULT 'pendiente'::character varying CHECK ("estadoRegistro"::text = ANY (ARRAY['pendiente'::character varying, 'aprobado'::character varying, 'rechazado'::character varying]::text[])),
  multaActiva boolean DEFAULT false,
  bloqueado boolean DEFAULT false,
  CONSTRAINT clientes_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_clientes_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador),
  CONSTRAINT fk_clientes_empleados FOREIGN KEY (verificador) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_clientes_paises FOREIGN KEY (numeropais) REFERENCES public.paises(numero)
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
CREATE TABLE public.empleados (
  identificador integer NOT NULL,
  cargo character varying,
  sector integer,
  CONSTRAINT empleados_pkey PRIMARY KEY (identificador)
);
CREATE TABLE public.fotos (
  identificador integer NOT NULL DEFAULT nextval('fotos_identificador_seq'::regclass),
  producto integer NOT NULL,
  url character varying NOT NULL,
  CONSTRAINT fotos_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_fotos_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador)
);
CREATE TABLE public.itemscatalogo (
  identificador integer NOT NULL DEFAULT nextval('itemscatalogo_identificador_seq'::regclass),
  catalogo integer NOT NULL,
  producto integer NOT NULL,
  preciobase numeric NOT NULL CHECK (preciobase > 0.01),
  comision numeric NOT NULL CHECK (comision > 0.01),
  subastado character varying CHECK (subastado::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  CONSTRAINT itemscatalogo_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_itemscatalogo_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador),
  CONSTRAINT fk_itemscatalogo_catalogos FOREIGN KEY (catalogo) REFERENCES public.catalogos(identificador)
);
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
  estado character varying CHECK (estado::text = ANY (ARRAY['activo'::character varying, 'inactivo'::character varying]::text[])),
  fotoFrente character varying,
  email character varying UNIQUE,
  password_hash character varying,
  fotoDorso character varying,
  CONSTRAINT personas_pkey PRIMARY KEY (identificador)
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
  estado character varying CHECK (estado::text = ANY (ARRAY['abierta'::character varying, 'cerrada'::character varying]::text[])),
  subastador integer,
  ubicacion character varying,
  capacidadasistentes integer,
  tienedeposito character varying CHECK (tienedeposito::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  seguridadpropia character varying CHECK (seguridadpropia::text = ANY (ARRAY['si'::character varying, 'no'::character varying]::text[])),
  categoria character varying CHECK (categoria::text = ANY (ARRAY['comun'::character varying, 'especial'::character varying, 'plata'::character varying, 'oro'::character varying, 'platino'::character varying]::text[])),
  CONSTRAINT subastas_pkey PRIMARY KEY (identificador),
  CONSTRAINT fk_subastas_subastadores FOREIGN KEY (subastador) REFERENCES public.subastadores(identificador)
);