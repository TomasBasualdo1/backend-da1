# 11 · Database

Motor: **PostgreSQL** (Supabase). Acceso: **SQL crudo con psycopg3** (sin ORM). Esquema snapshot: `db/Estructura-PostgreSQL-da1-updated.sql` (26 tablas).

> El header del `.sql` advierte: *"This schema is for context only and is not meant to be run"*. Es el reflejo del esquema real, pero el orden/constraints pueden no ser ejecutables tal cual.

## Modelo de personas (herencia por tabla)

`personas` es la base; las especializaciones comparten PK (`identificador`) por FK 1:1.

```
personas (identificador, documento, nombre, direccion, estado, foto)
├── personas_adicionales (email UNIQUE, password_hash, foto_frente/dorso, telefono, token_email, foto_url)
├── clientes (numeropais, admitido si/no, categoria, verificador→empleados)
│   └── clientes_adicionales (estado_registro, multa_activa, bloqueado, motivo_rechazo)
├── duenios (verificacionfinanciera, verificacionjudicial, calificacionriesgo 1-6, verificador)
├── empleados (cargo, sector)
└── subastadores (matricula, region)   ← martilleros/rematadores
```

> Un usuario de la app vive en `personas` + `personas_adicionales` + `clientes` + `clientes_adicionales`. Al consignar, además se le crea fila en `duenios` (`ensure_duenio`).

## Núcleo de subastas

```
subastas (identificador, fecha[>hoy+10d], hora, estado abierta/cerrada, subastador, ubicacion,
          capacidadasistentes, tienedeposito, seguridadpropia, categoria)
catalogos (descripcion, subasta→subastas, responsable→empleados)
itemscatalogo (catalogo→catalogos, producto→productos, preciobase>0.01, comision>0.01, subastado si/no)
asistentes (numeropostor, cliente→clientes, subasta→subastas)   ← participación
pujos (asistente→asistentes, item→itemscatalogo, importe>0.01, ganador si/no)   ← ofertas
registrodesubasta (subasta, duenio, producto, cliente, importe, comision)        ← ventas cerradas
sesiones_subasta (subasta_id, cliente_id, estado activa/finalizada, fecha_hora_inicio) ← presencia / SSE
```

## Productos y consignación (dos mundos, no confundir)

- **Legado / sistema empresa**: `productos` (descripcioncatalogo, descripcioncompleta, revisor→empleados, duenio→duenios, seguro→seguros) + `fotos` (bytea).
- **Consignación app (nuevo)**: `articulos` (duenio_id, descripcion, historia, artista, estado, precio_base_propuesto, comision_propuesta, tasacion_aceptada, seguro_poliza→seguros, fotos ARRAY, documentacion_origen ARRAY) + `fotos_adicionales` (foto_url, producto→productos).

**Flujo**: `articulos` (aprobado + tasación aceptada) → crea `seguros` + `productos` + copia fotos a `fotos_adicionales` → `productos` se agrega a `itemscatalogo`. Ver [07_DOMAIN_NOTES.md](07_DOMAIN_NOTES.md).

> ⚠ `fotos` (bytea, ligada a `productos`) vs `fotos_adicionales` (URL string) vs `articulos.fotos` (ARRAY de URLs). Tres lugares distintos para imágenes. `GET /uploads/fotos/{id}` lee de `fotos` (bytea).

## Pagos y penalizaciones

```
medios_pago (cliente_id, tipo[tarjeta_credito/cuenta_bancaria/cheque_certificado],
             datos_encriptados, ultimos_digitos, estado_verificacion, moneda ARS/USD,
             limite_reservado, pais_banco, es_cuenta_receptora)
pagos (subasta_id, cliente_id, total_pujado, comision, costo_envio, total_final, moneda,
       modo_entrega envio/retiro, direccion_envio, estado pendiente/pagado/vencido,
       fecha_limite_pago, medio_pago_id, acepta_perder_seguro)
multas (cliente_id, importe, estado pendiente/pagada, fecha_limite, motivo, medio_pago_id)
seguros (nropoliza PK, compania, polizacombinada si/no, importe>0)
```

## Otros

```
notificaciones (persona_id, tipo pago/subasta/sistema, mensaje, fecha_hora, leida)
blacklisted_tokens (jti PK, expires_at)   ← logout / revocación JWT
paises (numero PK, nombre, nombrecorto, capital, nacionalidad, idiomas)
sectores (nombresector, codigosector, responsablesector→empleados)
```

## Mapeo BD ↔ API (puntos a recordar)

- Columnas en **snake_case**; muchos responses en **camelCase** → los repos aliasen (`fecha_hora as "fechaHora"`).
- PK casi siempre se llama `identificador`; en responses se expone como `id`.
- `clientes.admitido` y varios flags usan strings `'si'/'no'` (no boolean); `clientes_adicionales`/`medios_pago`/`articulos` sí usan boolean.
- "Usuario" en el JWT = `personas.identificador` (mismo id que `clientes`).
- **Admin** = `personas.identificador == 1` (convención, no hay rol en BD para la API).

## Constraints de negocio embebidos en el esquema

- `subastas.fecha`: **sin restricción de antelación** (se eliminó la regla de "> hoy + 10 días"). Se removió la validación en `subasta_service.create_subasta` y el CHECK en BD vía `db/migration_remove_subastas_fecha_check.sql`. Ver [27_SUBASTAS_SIN_RESTRICCION_FECHA_NOTES.md](27_SUBASTAS_SIN_RESTRICCION_FECHA_NOTES.md).
- `itemscatalogo.preciobase`/`comision` y `pujos.importe` deben ser **> 0.01**.
- `personas_adicionales.email` es **UNIQUE**.
- Enums implementados como **CHECK constraints** sobre `varchar` (no tipos ENUM nativos de Postgres).
