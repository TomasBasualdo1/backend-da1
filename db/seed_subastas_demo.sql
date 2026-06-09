/*
Seed demo para subastas.

Uso local:
  DATABASE_URL="postgresql://usuario:password@host:puerto/db" psql "$DATABASE_URL" -f db/seed_subastas_demo.sql

Uso con Supabase:
  SUPABASE_DB_URL="postgresql://postgres.PROJECT_REF:password@aws-...pooler.supabase.com:6543/postgres" \
    psql "$SUPABASE_DB_URL" -f db/seed_subastas_demo.sql

Notas:
  - No hardcodea credenciales.
  - No borra datos reales.
  - Usa IDs explicitos en el rango 900000+ para mantener el seed idempotente.
  - Si una base real ya usa esos IDs, revisar antes de ejecutar.
  - Requiere que la tabla paises ya este cargada con Argentina = 1 y Uruguay = 3.
    Este seed no inserta ni modifica paises.
  - La tabla subastas no tiene columna moneda en el esquema actual. ARS/USD se
    dejan representadas en medios_pago y pagos, sin inventar columnas.
  - El CHECK de subastas.fecha exige fechas posteriores a CURRENT_DATE + 10 dias,
    por eso todas las subastas demo usan fechas futuras, incluso la cerrada.

Usuarios demo aprobados:
  Documento: DEMO-POSTOR-1 / Password: Demo1234!
  Documento: DEMO-POSTOR-2 / Password: Demo1234!
  Documento: DEMO-POSTOR-3 / Password: Demo1234!
  Documento: DEMO-POSTOR-4 / Password: Demo1234!

Verificacion rapida:
  SELECT identificador, fecha, hora, estado, categoria, ubicacion
  FROM subastas
  WHERE identificador BETWEEN 900001 AND 900006
  ORDER BY identificador;

  SELECT s.identificador AS subasta_id, c.identificador AS catalogo_id, COUNT(i.identificador) AS items
  FROM subastas s
  JOIN catalogos c ON c.subasta = s.identificador
  JOIN itemscatalogo i ON i.catalogo = c.identificador
  WHERE s.identificador BETWEEN 900001 AND 900006
  GROUP BY s.identificador, c.identificador
  ORDER BY s.identificador;
*/

BEGIN;

INSERT INTO public.personas (identificador, documento, nombre, direccion, estado, foto)
VALUES
  (900001, 'DEMO-EMP-1', 'Alicia Romano', 'Av. Corrientes 1200, CABA', 'activo', NULL),
  (900002, 'DEMO-SUB-1', 'Carla Ruiz', 'Av. Santa Fe 2400, CABA', 'activo', NULL),
  (900003, 'DEMO-SUB-2', 'Diego Suarez', 'Bv. San Juan 550, Cordoba', 'activo', NULL),
  (900004, 'DEMO-DUE-1', 'Julia Mendez', 'Calle Defensa 840, CABA', 'activo', NULL),
  (900005, 'DEMO-DUE-2', 'Martin Costa', 'San Martin 310, Mendoza', 'activo', NULL),
  (900006, 'DEMO-POSTOR-1', 'Luciana Vega', 'Lavalle 1550, CABA', 'activo', NULL),
  (900007, 'DEMO-POSTOR-2', 'Tomas Herrera', 'Belgrano 920, Rosario', 'activo', NULL),
  (900008, 'DEMO-POSTOR-3', 'Sofia Nieves', 'Colon 401, Cordoba', 'activo', NULL),
  (900009, 'DEMO-POSTOR-4', 'Pedro Alonso', 'Rambla Republica 1100, Montevideo', 'activo', NULL),
  (900010, 'DEMO-EMP-2', 'Valentina Castro', 'Godoy Cruz 1800, CABA', 'activo', NULL)
ON CONFLICT (identificador) DO UPDATE SET
  documento = EXCLUDED.documento,
  nombre = EXCLUDED.nombre,
  direccion = EXCLUDED.direccion,
  estado = EXCLUDED.estado;

INSERT INTO public.empleados (identificador, cargo, sector)
VALUES
  (900001, 'Coordinadora de operaciones demo', 900001),
  (900010, 'Responsable de catalogo demo', 900001)
ON CONFLICT (identificador) DO UPDATE SET
  cargo = EXCLUDED.cargo,
  sector = EXCLUDED.sector;

INSERT INTO public.sectores (identificador, nombresector, codigosector, responsablesector)
VALUES
  (900001, 'Operaciones y catalogos demo', 'DEMO-CAT', 900001)
ON CONFLICT (identificador) DO UPDATE SET
  nombresector = EXCLUDED.nombresector,
  codigosector = EXCLUDED.codigosector,
  responsablesector = EXCLUDED.responsablesector;

INSERT INTO public.subastadores (identificador, matricula, region)
VALUES
  (900002, 'MAT-DEMO-001', 'AMBA'),
  (900003, 'MAT-DEMO-002', 'Centro y Cuyo')
ON CONFLICT (identificador) DO UPDATE SET
  matricula = EXCLUDED.matricula,
  region = EXCLUDED.region;

INSERT INTO public.duenios (
  identificador, numeropais, verificacionfinanciera,
  verificacionjudicial, calificacionriesgo, verificador
)
VALUES
  (900004, 1, 'si', 'si', 2, 900001),
  (900005, 1, 'si', 'si', 1, 900001)
ON CONFLICT (identificador) DO UPDATE SET
  numeropais = EXCLUDED.numeropais,
  verificacionfinanciera = EXCLUDED.verificacionfinanciera,
  verificacionjudicial = EXCLUDED.verificacionjudicial,
  calificacionriesgo = EXCLUDED.calificacionriesgo,
  verificador = EXCLUDED.verificador;

INSERT INTO public.clientes (identificador, numeropais, admitido, categoria, verificador)
VALUES
  (900006, 1, 'si', 'comun', 900001),
  (900007, 1, 'si', 'plata', 900001),
  (900008, 1, 'si', 'oro', 900001),
  (900009, 3, 'si', 'platino', 900001)
ON CONFLICT (identificador) DO UPDATE SET
  numeropais = EXCLUDED.numeropais,
  admitido = EXCLUDED.admitido,
  categoria = EXCLUDED.categoria,
  verificador = EXCLUDED.verificador;

INSERT INTO public.personas_adicionales (
  identificador, email, password_hash, foto_frente, foto_dorso,
  telefono, token_email, foto_url
)
VALUES
  (900006, 'luciana.demo@example.com', '$2b$12$KG9QkR5wV1cuR9VqtmcKM.3Jnaj.G6bL7k4PD3UdF/AKey95j7cQ.', 'https://example.com/demo/dni/luciana-frente.jpg', 'https://example.com/demo/dni/luciana-dorso.jpg', '+54 11 5555-1001', NULL, 'https://example.com/demo/users/luciana.jpg'),
  (900007, 'tomas.demo@example.com', '$2b$12$KG9QkR5wV1cuR9VqtmcKM.3Jnaj.G6bL7k4PD3UdF/AKey95j7cQ.', 'https://example.com/demo/dni/tomas-frente.jpg', 'https://example.com/demo/dni/tomas-dorso.jpg', '+54 341 555-1002', NULL, 'https://example.com/demo/users/tomas.jpg'),
  (900008, 'sofia.demo@example.com', '$2b$12$KG9QkR5wV1cuR9VqtmcKM.3Jnaj.G6bL7k4PD3UdF/AKey95j7cQ.', 'https://example.com/demo/dni/sofia-frente.jpg', 'https://example.com/demo/dni/sofia-dorso.jpg', '+54 351 555-1003', NULL, 'https://example.com/demo/users/sofia.jpg'),
  (900009, 'pedro.demo@example.com', '$2b$12$KG9QkR5wV1cuR9VqtmcKM.3Jnaj.G6bL7k4PD3UdF/AKey95j7cQ.', 'https://example.com/demo/dni/pedro-frente.jpg', 'https://example.com/demo/dni/pedro-dorso.jpg', '+598 99 555 1004', NULL, 'https://example.com/demo/users/pedro.jpg')
ON CONFLICT (identificador) DO UPDATE SET
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  foto_frente = EXCLUDED.foto_frente,
  foto_dorso = EXCLUDED.foto_dorso,
  telefono = EXCLUDED.telefono,
  token_email = EXCLUDED.token_email,
  foto_url = EXCLUDED.foto_url;

INSERT INTO public.clientes_adicionales (
  identificador, estado_registro, multa_activa, bloqueado, motivo_rechazo
)
VALUES
  (900006, 'aprobado', false, false, NULL),
  (900007, 'aprobado', false, false, NULL),
  (900008, 'aprobado', false, false, NULL),
  (900009, 'aprobado', false, false, NULL)
ON CONFLICT (identificador) DO UPDATE SET
  estado_registro = EXCLUDED.estado_registro,
  multa_activa = EXCLUDED.multa_activa,
  bloqueado = EXCLUDED.bloqueado,
  motivo_rechazo = EXCLUDED.motivo_rechazo;

INSERT INTO public.seguros (nropoliza, compania, polizacombinada, importe)
VALUES
  ('DEMO-POL-ARTE-001', 'Rio de la Plata Seguros', 'si', 850000.00),
  ('DEMO-POL-JOYAS-001', 'Andes Patrimonial', 'no', 1250000.00),
  ('DEMO-POL-AUTOS-001', 'Mercosur Seguros', 'si', 4200000.00)
ON CONFLICT (nropoliza) DO UPDATE SET
  compania = EXCLUDED.compania,
  polizacombinada = EXCLUDED.polizacombinada,
  importe = EXCLUDED.importe;

INSERT INTO public.productos (
  identificador, fecha, disponible, descripcioncatalogo,
  descripcioncompleta, revisor, duenio, seguro
)
VALUES
  (900001, CURRENT_DATE - INTERVAL '45 days', 'si', 'Reloj de bolsillo suizo en plata', 'Reloj de bolsillo suizo circa 1910, caja de plata, mecanismo cuerda manual revisado.', 900010, 900004, 'DEMO-POL-ARTE-001'),
  (900002, CURRENT_DATE - INTERVAL '40 days', 'si', 'Juego de te ingles de porcelana', 'Juego de te de 18 piezas con sello de manufactura inglesa, excelente estado general.', 900010, 900004, 'DEMO-POL-ARTE-001'),
  (900003, CURRENT_DATE - INTERVAL '35 days', 'si', 'Oleo paisaje portuario firmado', 'Oleo sobre tela de escuela rioplatense, marco original y firma legible.', 900010, 900005, 'DEMO-POL-ARTE-001'),
  (900004, CURRENT_DATE - INTERVAL '34 days', 'si', 'Camara Leica M3 con lente 50mm', 'Camara Leica M3 con lente Summicron 50mm, estuche y correa originales.', 900010, 900005, 'DEMO-POL-ARTE-001'),
  (900005, CURRENT_DATE - INTERVAL '30 days', 'si', 'Anillo art deco con zafiro', 'Anillo art deco en oro blanco con zafiro central y pequenos diamantes laterales.', 900001, 900004, 'DEMO-POL-JOYAS-001'),
  (900006, CURRENT_DATE - INTERVAL '28 days', 'si', 'Collar de perlas cultivadas', 'Collar de perlas cultivadas con cierre de oro 18k, tasacion gemologica incluida.', 900001, 900004, 'DEMO-POL-JOYAS-001'),
  (900007, CURRENT_DATE - INTERVAL '24 days', 'si', 'Sillon escandinavo restaurado', 'Sillon de madera curvada y pana verde, restaurado por taller especializado.', 900010, 900005, 'DEMO-POL-ARTE-001'),
  (900008, CURRENT_DATE - INTERVAL '20 days', 'si', 'Escritorio frances de roble', 'Escritorio frances con cajonera lateral, herrajes originales y lustre restaurado.', 900010, 900005, 'DEMO-POL-ARTE-001'),
  (900009, CURRENT_DATE - INTERVAL '18 days', 'si', 'Guitarra criolla de luthier', 'Guitarra criolla de luthier argentino, tapa de cedro y aros de palisandro.', 900001, 900004, 'DEMO-POL-ARTE-001'),
  (900010, CURRENT_DATE - INTERVAL '14 days', 'si', 'Coleccion de monedas argentinas', 'Coleccion numismatica argentina 1881-1950 con album y fichas de procedencia.', 900001, 900005, 'DEMO-POL-JOYAS-001'),
  (900011, CURRENT_DATE - INTERVAL '12 days', 'no', 'Moto clasica restaurada 1968', 'Moto clasica restaurada con documentacion completa, motor encendido en inspeccion.', 900010, 900005, 'DEMO-POL-AUTOS-001'),
  (900012, CURRENT_DATE - INTERVAL '10 days', 'no', 'Lote de afiches de cine argentino', 'Lote de 12 afiches originales de cine argentino de decadas 60 y 70.', 900010, 900004, 'DEMO-POL-ARTE-001')
ON CONFLICT (identificador) DO UPDATE SET
  fecha = EXCLUDED.fecha,
  disponible = EXCLUDED.disponible,
  descripcioncatalogo = EXCLUDED.descripcioncatalogo,
  descripcioncompleta = EXCLUDED.descripcioncompleta,
  revisor = EXCLUDED.revisor,
  duenio = EXCLUDED.duenio,
  seguro = EXCLUDED.seguro;

INSERT INTO public.fotos (identificador, producto, foto)
VALUES
  (900001, 900001, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900002, 900002, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900003, 900003, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900004, 900004, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900005, 900005, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900006, 900006, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900007, 900007, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900008, 900008, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900009, 900009, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900010, 900010, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900011, 900011, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64')),
  (900012, 900012, decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=', 'base64'))
ON CONFLICT (identificador) DO UPDATE SET
  producto = EXCLUDED.producto,
  foto = EXCLUDED.foto;

INSERT INTO public.subastas (
  identificador, fecha, hora, estado, subastador, ubicacion,
  capacidadasistentes, tienedeposito, seguridadpropia, categoria
)
VALUES
  (900001, (CURRENT_DATE + INTERVAL '15 days')::date, TIME '19:00', 'abierta', 900002, 'Galeria Central, CABA', 80, 'si', 'si', 'comun'),
  (900002, (CURRENT_DATE + INTERVAL '21 days')::date, TIME '18:30', 'abierta', 900003, 'Salon Sierras, Cordoba', 60, 'si', 'no', 'especial'),
  (900003, (CURRENT_DATE + INTERVAL '28 days')::date, TIME '20:00', 'abierta', 900002, 'Hotel Diplomatic, Mendoza', 120, 'no', 'si', 'plata'),
  (900004, (CURRENT_DATE + INTERVAL '36 days')::date, TIME '17:00', 'abierta', 900003, 'Centro Cultural Fontanarrosa, Rosario', 90, 'si', 'si', 'oro'),
  (900005, (CURRENT_DATE + INTERVAL '45 days')::date, TIME '19:30', 'abierta', 900002, 'Club del Lago, Punta del Este', 70, 'no', 'si', 'platino'),
  (900006, (CURRENT_DATE + INTERVAL '60 days')::date, TIME '16:00', 'cerrada', 900003, 'Auditorio Mar del Plata', 50, 'si', 'no', 'comun')
ON CONFLICT (identificador) DO UPDATE SET
  fecha = EXCLUDED.fecha,
  hora = EXCLUDED.hora,
  estado = EXCLUDED.estado,
  subastador = EXCLUDED.subastador,
  ubicacion = EXCLUDED.ubicacion,
  capacidadasistentes = EXCLUDED.capacidadasistentes,
  tienedeposito = EXCLUDED.tienedeposito,
  seguridadpropia = EXCLUDED.seguridadpropia,
  categoria = EXCLUDED.categoria;

INSERT INTO public.catalogos (identificador, descripcion, subasta, responsable)
VALUES
  (900001, 'Catalogo demo de antiguedades accesibles', 900001, 900010),
  (900002, 'Catalogo demo de arte y fotografia', 900002, 900010),
  (900003, 'Catalogo demo de joyas seleccionadas', 900003, 900010),
  (900004, 'Catalogo demo de mobiliario y diseno', 900004, 900010),
  (900005, 'Catalogo demo de coleccionismo premium', 900005, 900010),
  (900006, 'Catalogo demo de cierre y adjudicaciones', 900006, 900010)
ON CONFLICT (identificador) DO UPDATE SET
  descripcion = EXCLUDED.descripcion,
  subasta = EXCLUDED.subasta,
  responsable = EXCLUDED.responsable;

INSERT INTO public.itemscatalogo (
  identificador, catalogo, producto, preciobase, comision, subastado
)
VALUES
  (900001, 900001, 900001, 45000.00, 4500.00, 'no'),
  (900002, 900001, 900002, 65000.00, 6500.00, 'no'),
  (900003, 900002, 900003, 180000.00, 18000.00, 'no'),
  (900004, 900002, 900004, 950000.00, 95000.00, 'no'),
  (900005, 900003, 900005, 720000.00, 72000.00, 'no'),
  (900006, 900003, 900006, 360000.00, 36000.00, 'no'),
  (900007, 900004, 900007, 210000.00, 21000.00, 'no'),
  (900008, 900004, 900008, 480000.00, 48000.00, 'no'),
  (900009, 900005, 900009, 250000.00, 25000.00, 'no'),
  (900010, 900005, 900010, 1200000.00, 120000.00, 'no'),
  (900011, 900006, 900011, 3100000.00, 310000.00, 'si'),
  (900012, 900006, 900012, 90000.00, 9000.00, 'si')
ON CONFLICT (identificador) DO UPDATE SET
  catalogo = EXCLUDED.catalogo,
  producto = EXCLUDED.producto,
  preciobase = EXCLUDED.preciobase,
  comision = EXCLUDED.comision,
  subastado = EXCLUDED.subastado;

INSERT INTO public.asistentes (identificador, numeropostor, cliente, subasta)
VALUES
  (900001, 101, 900006, 900001),
  (900002, 102, 900007, 900001),
  (900003, 103, 900008, 900001),
  (900004, 201, 900007, 900002),
  (900005, 202, 900009, 900002),
  (900006, 301, 900008, 900003),
  (900007, 302, 900009, 900003),
  (900008, 401, 900009, 900004),
  (900009, 501, 900008, 900005),
  (900010, 601, 900006, 900006),
  (900011, 602, 900007, 900006)
ON CONFLICT (identificador) DO UPDATE SET
  numeropostor = EXCLUDED.numeropostor,
  cliente = EXCLUDED.cliente,
  subasta = EXCLUDED.subasta;

INSERT INTO public.pujos (identificador, asistente, item, importe, ganador)
VALUES
  (900001, 900001, 900001, 47000.00, 'no'),
  (900002, 900002, 900001, 49500.00, 'si'),
  (900003, 900003, 900002, 72000.00, 'si'),
  (900004, 900004, 900003, 195000.00, 'si'),
  (900005, 900005, 900004, 1010000.00, 'si'),
  (900006, 900006, 900005, 760000.00, 'no'),
  (900007, 900007, 900005, 815000.00, 'si'),
  (900008, 900007, 900006, 388000.00, 'si'),
  (900009, 900008, 900007, 226000.00, 'si'),
  (900010, 900009, 900010, 1280000.00, 'si'),
  (900011, 900010, 900011, 3350000.00, 'si'),
  (900012, 900011, 900012, 118000.00, 'si')
ON CONFLICT (identificador) DO UPDATE SET
  asistente = EXCLUDED.asistente,
  item = EXCLUDED.item,
  importe = EXCLUDED.importe,
  ganador = EXCLUDED.ganador;

INSERT INTO public.registrodesubasta (
  identificador, subasta, duenio, producto, cliente, importe, comision
)
VALUES
  (900001, 900006, 900005, 900011, 900006, 3350000.00, 310000.00),
  (900002, 900006, 900004, 900012, 900007, 118000.00, 9000.00)
ON CONFLICT (identificador) DO UPDATE SET
  subasta = EXCLUDED.subasta,
  duenio = EXCLUDED.duenio,
  producto = EXCLUDED.producto,
  cliente = EXCLUDED.cliente,
  importe = EXCLUDED.importe,
  comision = EXCLUDED.comision;

INSERT INTO public.medios_pago (
  identificador, cliente_id, tipo, datos_encriptados, ultimos_digitos,
  estado_verificacion, moneda, limite_reservado, pais_banco, es_cuenta_receptora
)
VALUES
  (900001, 900006, 'tarjeta_credito', 'demo-token-tc-1001', '1001', 'validado', 'ARS', 600000.00, 'AR', false),
  (900002, 900007, 'cuenta_bancaria', 'demo-token-cb-2002', '2002', 'validado', 'ARS', 900000.00, 'AR', false),
  (900003, 900008, 'tarjeta_credito', 'demo-token-tc-3003', '3003', 'validado', 'USD', 12000.00, 'US', false),
  (900004, 900009, 'cheque_certificado', 'demo-token-ch-4004', '4004', 'validado', 'USD', 25000.00, 'UY', false)
ON CONFLICT (identificador) DO UPDATE SET
  cliente_id = EXCLUDED.cliente_id,
  tipo = EXCLUDED.tipo,
  datos_encriptados = EXCLUDED.datos_encriptados,
  ultimos_digitos = EXCLUDED.ultimos_digitos,
  estado_verificacion = EXCLUDED.estado_verificacion,
  moneda = EXCLUDED.moneda,
  limite_reservado = EXCLUDED.limite_reservado,
  pais_banco = EXCLUDED.pais_banco,
  es_cuenta_receptora = EXCLUDED.es_cuenta_receptora;

INSERT INTO public.pagos (
  identificador, subasta_id, cliente_id, total_pujado, comision, costo_envio,
  total_final, moneda, modo_entrega, direccion_envio, estado,
  fecha_limite_pago, medio_pago_id, acepta_perder_seguro
)
VALUES
  (900001, 900006, 900006, 3350000.00, 310000.00, 25000.00, 3685000.00, 'ARS', 'envio', 'Lavalle 1550, CABA', 'pendiente', CURRENT_TIMESTAMP + INTERVAL '7 days', 900001, false),
  (900002, 900006, 900007, 118000.00, 9000.00, 0.00, 127000.00, 'ARS', 'retiro', NULL, 'pagado', CURRENT_TIMESTAMP + INTERVAL '7 days', 900002, false)
ON CONFLICT (identificador) DO UPDATE SET
  subasta_id = EXCLUDED.subasta_id,
  cliente_id = EXCLUDED.cliente_id,
  total_pujado = EXCLUDED.total_pujado,
  comision = EXCLUDED.comision,
  costo_envio = EXCLUDED.costo_envio,
  total_final = EXCLUDED.total_final,
  moneda = EXCLUDED.moneda,
  modo_entrega = EXCLUDED.modo_entrega,
  direccion_envio = EXCLUDED.direccion_envio,
  estado = EXCLUDED.estado,
  fecha_limite_pago = EXCLUDED.fecha_limite_pago,
  medio_pago_id = EXCLUDED.medio_pago_id,
  acepta_perder_seguro = EXCLUDED.acepta_perder_seguro;

INSERT INTO public.sesiones_subasta (
  identificador, subasta_id, cliente_id, estado, fecha_hora_inicio
)
VALUES
  (900001, 900001, 900006, 'activa', CURRENT_TIMESTAMP - INTERVAL '10 minutes'),
  (900002, 900002, 900007, 'activa', CURRENT_TIMESTAMP - INTERVAL '20 minutes'),
  (900003, 900006, 900006, 'finalizada', CURRENT_TIMESTAMP - INTERVAL '2 days')
ON CONFLICT (identificador) DO UPDATE SET
  subasta_id = EXCLUDED.subasta_id,
  cliente_id = EXCLUDED.cliente_id,
  estado = EXCLUDED.estado,
  fecha_hora_inicio = EXCLUDED.fecha_hora_inicio;

INSERT INTO public.notificaciones (
  identificador, persona_id, tipo, mensaje, fecha_hora, leida
)
VALUES
  (900001, 900006, 'subasta', 'Ya estas inscripto en la subasta demo de antiguedades accesibles.', CURRENT_TIMESTAMP - INTERVAL '1 day', false),
  (900002, 900007, 'pago', 'Tenes un pago demo registrado para la subasta de cierre.', CURRENT_TIMESTAMP - INTERVAL '3 hours', false),
  (900003, 900008, 'subasta', 'Nueva puja demo superada en un item de coleccionismo.', CURRENT_TIMESTAMP - INTERVAL '45 minutes', true)
ON CONFLICT (identificador) DO UPDATE SET
  persona_id = EXCLUDED.persona_id,
  tipo = EXCLUDED.tipo,
  mensaje = EXCLUDED.mensaje,
  fecha_hora = EXCLUDED.fecha_hora,
  leida = EXCLUDED.leida;

COMMIT;
