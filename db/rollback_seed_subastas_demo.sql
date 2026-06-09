/*
Rollback del seed demo de subastas.

Uso local:
  DATABASE_URL="postgresql://usuario:password@host:puerto/db" psql "$DATABASE_URL" -f db/rollback_seed_subastas_demo.sql

Uso con Supabase:
  SUPABASE_DB_URL="postgresql://postgres.PROJECT_REF:password@aws-...pooler.supabase.com:6543/postgres" \
    psql "$SUPABASE_DB_URL" -f db/rollback_seed_subastas_demo.sql

Notas:
  - Borra solo los registros demo creados por db/seed_subastas_demo.sql.
  - No borra ni modifica paises.
  - No borra datos reales fuera de los IDs/codigos demo explicitamente listados.
  - Ejecuta las eliminaciones en orden inverso de foreign keys.
*/

BEGIN;

DELETE FROM public.notificaciones
WHERE identificador IN (900001, 900002, 900003);

DELETE FROM public.sesiones_subasta
WHERE identificador IN (900001, 900002, 900003);

DELETE FROM public.pagos
WHERE identificador IN (900001, 900002);

DELETE FROM public.medios_pago
WHERE identificador IN (900001, 900002, 900003, 900004);

DELETE FROM public.registrodesubasta
WHERE identificador IN (900001, 900002);

DELETE FROM public.pujos
WHERE identificador BETWEEN 900001 AND 900012;

DELETE FROM public.asistentes
WHERE identificador BETWEEN 900001 AND 900011;

DELETE FROM public.itemscatalogo
WHERE identificador BETWEEN 900001 AND 900012;

DELETE FROM public.catalogos
WHERE identificador BETWEEN 900001 AND 900006;

DELETE FROM public.subastas
WHERE identificador BETWEEN 900001 AND 900006;

DELETE FROM public.fotos
WHERE identificador BETWEEN 900001 AND 900012;

DELETE FROM public.fotos_adicionales
WHERE identificador BETWEEN 900001 AND 900012;

DELETE FROM public.productos
WHERE identificador BETWEEN 900001 AND 900012;

DELETE FROM public.seguros
WHERE nropoliza IN ('DEMO-POL-ARTE-001', 'DEMO-POL-JOYAS-001', 'DEMO-POL-AUTOS-001');

DELETE FROM public.clientes_adicionales
WHERE identificador IN (900006, 900007, 900008, 900009);

DELETE FROM public.personas_adicionales
WHERE identificador IN (900006, 900007, 900008, 900009);

DELETE FROM public.clientes
WHERE identificador IN (900006, 900007, 900008, 900009);

DELETE FROM public.duenios
WHERE identificador IN (900004, 900005);

DELETE FROM public.subastadores
WHERE identificador IN (900002, 900003);

DELETE FROM public.sectores
WHERE identificador = 900001;

DELETE FROM public.empleados
WHERE identificador IN (900001, 900010);

DELETE FROM public.personas
WHERE identificador BETWEEN 900001 AND 900010
  AND documento LIKE 'DEMO-%';

COMMIT;
