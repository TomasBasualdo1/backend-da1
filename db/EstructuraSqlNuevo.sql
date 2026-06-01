-- DROP TABLES IF EXISTS IN REVERSE DEPENDENCY ORDER
DROP TABLE IF EXISTS public.sesiones_subasta CASCADE;
DROP TABLE IF EXISTS public.pagos CASCADE;
DROP TABLE IF EXISTS public.articulos CASCADE;
DROP TABLE IF EXISTS public.blacklisted_tokens CASCADE;
DROP TABLE IF EXISTS public.notificaciones CASCADE;
DROP TABLE IF EXISTS public.multas CASCADE;
DROP TABLE IF EXISTS public.medios_pago CASCADE;
DROP TABLE IF EXISTS public.clientes_adicionales CASCADE;
DROP TABLE IF EXISTS public.personas_adicionales CASCADE;
DROP TABLE IF EXISTS public.registrodesubasta CASCADE;
DROP TABLE IF EXISTS public.pujos CASCADE;
DROP TABLE IF EXISTS public.asistentes CASCADE;
DROP TABLE IF EXISTS public.itemscatalogo CASCADE;
DROP TABLE IF EXISTS public.catalogos CASCADE;
DROP TABLE IF EXISTS public.fotos CASCADE;
DROP TABLE IF EXISTS public.productos CASCADE;
DROP TABLE IF EXISTS public.subastas CASCADE;
DROP TABLE IF EXISTS public.subastadores CASCADE;
DROP TABLE IF EXISTS public.duenios CASCADE;
DROP TABLE IF EXISTS public.clientes CASCADE;
DROP TABLE IF EXISTS public.seguros CASCADE;
DROP TABLE IF EXISTS public.sectores CASCADE;
DROP TABLE IF EXISTS public.empleados CASCADE;
DROP TABLE IF EXISTS public.personas CASCADE;
DROP TABLE IF EXISTS public.paises CASCADE;

-- ============================================================================
-- 1. TABLAS BASE DEL PROFESOR (TRADUCIDAS A POSTGRESQL SIN MODIFICACIONES)
-- ============================================================================

CREATE TABLE public.paises (
  numero integer NOT NULL,
  nombre character varying(250) NOT NULL,
  nombrecorto character varying(250),
  capital character varying(250) NOT NULL,
  nacionalidad character varying(250) NOT NULL,
  idiomas character varying(150) NOT NULL,
  CONSTRAINT pk_paises PRIMARY KEY (numero)
);

CREATE TABLE public.personas (
  identificador serial NOT NULL,
  documento character varying(20) NOT NULL,
  nombre character varying(150) NOT NULL,
  direccion character varying(250),
  estado character varying(15) CHECK (estado IN ('activo', 'inactivo', 'incativo')),
  foto bytea,
  CONSTRAINT pk_personas PRIMARY KEY (identificador)
);

CREATE TABLE public.empleados (
  identificador integer NOT NULL,
  cargo character varying(100),
  sector integer,
  CONSTRAINT pk_empleados PRIMARY KEY (identificador)
);

CREATE TABLE public.sectores (
  identificador serial NOT NULL,
  nombresector character varying(150) NOT NULL,
  codigosector character varying(10),
  responsablesector integer,
  CONSTRAINT pk_sectores PRIMARY KEY (identificador),
  CONSTRAINT fk_sectores_empleados FOREIGN KEY (responsablesector) REFERENCES public.empleados(identificador)
);

CREATE TABLE public.seguros (
  nropoliza character varying(30) NOT NULL,
  compania character varying(150) NOT NULL,
  polizacombinada character varying(2) CHECK (polizacombinada IN ('si', 'no')),
  importe numeric(18,2) NOT NULL CHECK (importe > 0),
  CONSTRAINT pk_seguro PRIMARY KEY (nropoliza)
);

CREATE TABLE public.clientes (
  identificador integer NOT NULL,
  numeropais integer,
  admitido character varying(2) CHECK (admitido IN ('si', 'no')),
  categoria character varying(10) CHECK (categoria IN ('comun', 'especial', 'plata', 'oro', 'platino')),
  verificador integer NOT NULL,
  CONSTRAINT pk_clientes PRIMARY KEY (identificador),
  CONSTRAINT fk_clientes_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador),
  CONSTRAINT fk_clientes_empleados FOREIGN KEY (verificador) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_clientes_paises FOREIGN KEY (numeropais) REFERENCES public.paises(numero)
);

CREATE TABLE public.duenios (
  identificador integer NOT NULL,
  numeropais integer,
  verificacionfinanciera character varying(2) CHECK (verificacionfinanciera IN ('si', 'no')),
  verificacionjudicial character varying(2) CHECK (verificacionjudicial IN ('si', 'no')),
  calificacionriesgo integer CHECK (calificacionriesgo IN (1, 2, 3, 4, 5, 6)),
  verificador integer NOT NULL,
  CONSTRAINT pk_duenios PRIMARY KEY (identificador),
  CONSTRAINT fk_duenios_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador),
  CONSTRAINT fk_duenios_empleados FOREIGN KEY (verificador) REFERENCES public.empleados(identificador)
);

CREATE TABLE public.subastadores (
  identificador integer NOT NULL,
  matricula character varying(15),
  region character varying(50),
  CONSTRAINT pk_subastadores PRIMARY KEY (identificador),
  CONSTRAINT fk_subastadores_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador)
);

CREATE TABLE public.subastas (
  identificador serial NOT NULL,
  fecha date CHECK (fecha > (CURRENT_DATE + '10 days'::interval)::date),
  hora time without time zone NOT NULL,
  estado character varying(10) CHECK (estado IN ('abierta', 'cerrada', 'carrada')),
  subastador integer,
  ubicacion character varying(350),
  capacidadasistentes integer,
  tienedeposito character varying(2) CHECK (tienedeposito IN ('si', 'no')),
  seguridadpropia character varying(2) CHECK (seguridadpropia IN ('si', 'no')),
  categoria character varying(10) CHECK (categoria IN ('comun', 'especial', 'plata', 'oro', 'platino')),
  CONSTRAINT pk_subastas PRIMARY KEY (identificador),
  CONSTRAINT fk_subastas_subastadores FOREIGN KEY (subastador) REFERENCES public.subastadores(identificador)
);

CREATE TABLE public.productos (
  identificador serial NOT NULL,
  fecha date,
  disponible character varying(2) CHECK (disponible IN ('si', 'no')),
  descripcioncatalogo character varying(500) DEFAULT 'No Posee',
  descripcioncompleta character varying(300) NOT NULL,
  revisor integer NOT NULL,
  duenio integer NOT NULL,
  seguro character varying(30),
  CONSTRAINT pk_productos PRIMARY KEY (identificador),
  CONSTRAINT fk_productos_empleados FOREIGN KEY (revisor) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_productos_duenios FOREIGN KEY (duenio) REFERENCES public.duenios(identificador)
);

CREATE TABLE public.fotos (
  identificador serial NOT NULL,
  producto integer NOT NULL,
  foto bytea NOT NULL,
  CONSTRAINT pk_fotos PRIMARY KEY (identificador),
  CONSTRAINT fk_fotos_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador)
);

CREATE TABLE public.catalogos (
  identificador serial NOT NULL,
  descripcion character varying(250) NOT NULL,
  subasta integer,
  responsable integer NOT NULL,
  CONSTRAINT pk_catalogos PRIMARY KEY (identificador),
  CONSTRAINT fk_catalogos_empleados FOREIGN KEY (responsable) REFERENCES public.empleados(identificador),
  CONSTRAINT fk_catalogos_subastas FOREIGN KEY (subasta) REFERENCES public.subastas(identificador)
);

CREATE TABLE public.itemscatalogo (
  identificador serial NOT NULL,
  catalogo integer NOT NULL,
  producto integer NOT NULL,
  preciobase numeric(18,2) NOT NULL CHECK (preciobase > 0.01),
  comision numeric(18,2) NOT NULL CHECK (comision > 0.01),
  subastado character varying(2) CHECK (subastado IN ('si', 'no')),
  CONSTRAINT pk_itemscatalogo PRIMARY KEY (identificador),
  CONSTRAINT fk_itemscatalogo_catalogos FOREIGN KEY (catalogo) REFERENCES public.catalogos(identificador),
  CONSTRAINT fk_itemscatalogo_productos FOREIGN KEY (producto) REFERENCES public.productos(identificador)
);

CREATE TABLE public.asistentes (
  identificador serial NOT NULL,
  numeropostor integer NOT NULL,
  cliente integer NOT NULL,
  subasta integer NOT NULL,
  CONSTRAINT pk_asistentes PRIMARY KEY (identificador),
  CONSTRAINT fk_asistentes_clientes FOREIGN KEY (cliente) REFERENCES public.clientes(identificador),
  CONSTRAINT fk_asistentes_subasta FOREIGN KEY (subasta) REFERENCES public.subastas(identificador)
);

CREATE TABLE public.pujos (
  identificador serial NOT NULL,
  asistente integer NOT NULL,
  item integer NOT NULL,
  importe numeric(18,2) NOT NULL CHECK (importe > 0.01),
  ganador character varying(2) DEFAULT 'no' CHECK (ganador IN ('si', 'no')),
  CONSTRAINT pk_pujos PRIMARY KEY (identificador),
  CONSTRAINT fk_pujos_asistentes FOREIGN KEY (asistente) REFERENCES public.asistentes(identificador),
  CONSTRAINT fk_pujos_itemscatalogo FOREIGN KEY (item) REFERENCES public.itemscatalogo(identificador)
);

CREATE TABLE public.registrodesubasta (
  identificador serial NOT NULL,
  subasta integer NOT NULL,
  duenio integer NOT NULL,
  producto integer NOT NULL,
  cliente integer NOT NULL,
  importe numeric(18,2) NOT NULL CHECK (importe > 0.01),
  comision numeric(18,2) NOT NULL CHECK (comision > 0.01),
  CONSTRAINT pk_registrodesubasta PRIMARY KEY (identificador),
  CONSTRAINT fk_registrodesubasta_subastas FOREIGN KEY (subasta) REFERENCES public.subastas(identificador),
  CONSTRAINT fk_registrodesubasta_duenios FOREIGN KEY (duenio) REFERENCES public.duenios(identificador),
  CONSTRAINT fk_registrodesubasta_producto FOREIGN KEY (producto) REFERENCES public.productos(identificador),
  CONSTRAINT fk_registrodesubasta_cliente FOREIGN KEY (cliente) REFERENCES public.clientes(identificador)
);


-- ============================================================================
-- 2. TABLAS DE EXTENSIÓN (NUEVOS ATRIBUTOS PARA TABLAS BASE)
-- ============================================================================

CREATE TABLE public.personas_adicionales (
  identificador integer NOT NULL,
  email character varying(250) UNIQUE,
  password_hash character varying(250),
  foto_frente character varying(500),
  foto_dorso character varying(500),
  telefono character varying(50),
  token_email character varying(250),
  CONSTRAINT pk_personas_adicionales PRIMARY KEY (identificador),
  CONSTRAINT fk_personas_adicionales_personas FOREIGN KEY (identificador) REFERENCES public.personas(identificador) ON DELETE CASCADE
);

CREATE TABLE public.clientes_adicionales (
  identificador integer NOT NULL,
  estado_registro character varying(20) DEFAULT 'pendiente' CHECK (estado_registro IN ('pendiente', 'aprobado', 'rechazado')),
  multa_activa boolean DEFAULT false,
  bloqueado boolean DEFAULT false,
  motivo_rechazo character varying(500),
  CONSTRAINT pk_clientes_adicionales PRIMARY KEY (identificador),
  CONSTRAINT fk_clientes_adicionales_clientes FOREIGN KEY (identificador) REFERENCES public.clientes(identificador) ON DELETE CASCADE
);


-- ============================================================================
-- 3. TABLAS NUEVAS REQUERIDAS POR EL SWAGGER (NUEVAS ENTIDADES)
-- ============================================================================

CREATE TABLE public.medios_pago (
  identificador serial NOT NULL,
  cliente_id integer NOT NULL,
  tipo character varying(50) NOT NULL CHECK (tipo IN ('tarjeta_credito', 'cuenta_bancaria', 'cheque_certificado')),
  datos_encriptados character varying(500) NOT NULL,
  ultimos_digitos character varying(4) NOT NULL,
  estado_verificacion character varying(20) DEFAULT 'pendiente' CHECK (estado_verificacion IN ('pendiente', 'validado', 'rechazado')),
  moneda character varying(3) NOT NULL CHECK (moneda IN ('ARS', 'USD')),
  limite_reservado numeric(18,2) DEFAULT 0.00 CHECK (limite_reservado >= 0),
  pais_banco character varying(50),
  es_cuenta_receptora boolean DEFAULT false,
  CONSTRAINT pk_medios_pago PRIMARY KEY (identificador),
  CONSTRAINT fk_medios_pago_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador) ON DELETE CASCADE
);

CREATE TABLE public.multas (
  identificador serial NOT NULL,
  cliente_id integer NOT NULL,
  importe numeric(18,2) NOT NULL CHECK (importe > 0),
  estado character varying(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'pagada')),
  fecha_limite timestamp with time zone NOT NULL,
  motivo character varying(500),
  medio_pago_id integer,
  CONSTRAINT pk_multas PRIMARY KEY (identificador),
  CONSTRAINT fk_multas_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador) ON DELETE CASCADE,
  CONSTRAINT fk_multas_medios_pago FOREIGN KEY (medio_pago_id) REFERENCES public.medios_pago(identificador) ON DELETE SET NULL
);

CREATE TABLE public.notificaciones (
  identificador serial NOT NULL,
  persona_id integer NOT NULL,
  tipo character varying(20) NOT NULL CHECK (tipo IN ('pago', 'subasta', 'sistema')),
  mensaje character varying(1000) NOT NULL,
  fecha_hora timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  leida boolean DEFAULT false,
  CONSTRAINT pk_notificaciones PRIMARY KEY (identificador),
  CONSTRAINT fk_notificaciones_personas FOREIGN KEY (persona_id) REFERENCES public.personas(identificador) ON DELETE CASCADE
);

CREATE TABLE public.blacklisted_tokens (
  jti character varying(250) NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  CONSTRAINT pk_blacklisted_tokens PRIMARY KEY (jti)
);

CREATE TABLE public.articulos (
  identificador serial NOT NULL,
  duenio_id integer NOT NULL,
  descripcion character varying(500) NOT NULL,
  historia character varying(2000),
  artista character varying(250),
  fecha_creacion date,
  es_propietario boolean DEFAULT true,
  declara_origen_licito boolean DEFAULT true,
  estado character varying(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en_inspeccion', 'aprobado', 'rechazado', 'devuelto')),
  motivo_rechazo character varying(500),
  precio_base_propuesto numeric(18,2),
  comision_propuesta numeric(18,2),
  tasacion_aceptada boolean,
  fecha_envio timestamp with time zone,
  ubicacion character varying(250) DEFAULT 'Deposito CABA',
  seguro_poliza character varying(30),
  fotos character varying[],
  documentacion_origen character varying[],
  CONSTRAINT pk_articulos PRIMARY KEY (identificador),
  CONSTRAINT fk_articulos_duenios FOREIGN KEY (duenio_id) REFERENCES public.duenios(identificador) ON DELETE CASCADE,
  CONSTRAINT fk_articulos_seguros FOREIGN KEY (seguro_poliza) REFERENCES public.seguros(nropoliza) ON DELETE SET NULL
);

CREATE TABLE public.pagos (
  identificador serial NOT NULL,
  subasta_id integer NOT NULL,
  cliente_id integer NOT NULL,
  total_pujado numeric(18,2) NOT NULL CHECK (total_pujado >= 0),
  comision numeric(18,2) NOT NULL CHECK (comision >= 0),
  costo_envio numeric(18,2) DEFAULT 0.00 CHECK (costo_envio >= 0),
  total_final numeric(18,2) NOT NULL CHECK (total_final >= 0),
  moneda character varying(3) NOT NULL CHECK (moneda IN ('ARS', 'USD')),
  modo_entrega character varying(20) CHECK (modo_entrega IN ('envio', 'retiro')),
  direccion_envio character varying(500),
  estado character varying(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'pagado', 'vencido')),
  fecha_limite_pago timestamp with time zone NOT NULL,
  medio_pago_id integer,
  acepta_perder_seguro boolean DEFAULT false,
  CONSTRAINT pk_pagos PRIMARY KEY (identificador),
  CONSTRAINT fk_pagos_subastas FOREIGN KEY (subasta_id) REFERENCES public.subastas(identificador) ON DELETE CASCADE,
  CONSTRAINT fk_pagos_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador) ON DELETE CASCADE,
  CONSTRAINT fk_pagos_medios_pago FOREIGN KEY (medio_pago_id) REFERENCES public.medios_pago(identificador) ON DELETE SET NULL
);

CREATE TABLE public.sesiones_subasta (
  identificador serial NOT NULL,
  subasta_id integer NOT NULL,
  cliente_id integer NOT NULL,
  estado character varying(20) DEFAULT 'activa' CHECK (estado IN ('activa', 'finalizada')),
  fecha_hora_inicio timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pk_sesiones_subasta PRIMARY KEY (identificador),
  CONSTRAINT fk_sesiones_subasta_subastas FOREIGN KEY (subasta_id) REFERENCES public.subastas(identificador) ON DELETE CASCADE,
  CONSTRAINT fk_sesiones_subasta_clientes FOREIGN KEY (cliente_id) REFERENCES public.clientes(identificador) ON DELETE CASCADE
);
