from typing import Optional
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import (
    Usuario,
    UsuarioUpdate,
    MedioPago,
    MedioPagoInput,
    MedioPagoUpdate,
    UsuarioMetricas,
    Multa,
    MultaPagoRequest,
)
from app.services.storage_service import StorageService

router = APIRouter(prefix="/usuarios")


@router.get("/me", response_model=Usuario)
async def get_profile(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    query = """
        SELECT 
            p.identificador as id,
            p.documento,
            p.nombre as nombre_completo,
            p.direccion,
            pa.email,
            pa.telefono,
            pa.foto_url as foto,
            c.numeropais as "numeroPais",
            c.admitido,
            ca.estado_registro as "estadoRegistro",
            c.categoria,
            ca.multa_activa as "multaActiva",
            ca.bloqueado
        FROM personas p
        JOIN personas_adicionales pa ON p.identificador = pa.identificador
        JOIN clientes c ON p.identificador = c.identificador
        JOIN clientes_adicionales ca ON p.identificador = ca.identificador
        WHERE p.identificador = %s
    """
    with db.cursor() as cursor:
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Split the full name into nombre and apellido
    nombre_completo = row.get("nombre_completo") or ""
    parts = nombre_completo.split(" ", 1)
    nombre = parts[0]
    apellido = parts[1] if len(parts) > 1 else ""

    # Map admitido string 'si'/'no' to Admitido enum values
    db_admitido = row.get("admitido")
    admitido = "si" if db_admitido == "si" else False

    return Usuario(
        id=row["id"],
        documento=row["documento"],
        nombre=nombre,
        apellido=apellido,
        email=row["email"],
        direccion=row["direccion"],
        foto=row["foto"],
        numeroPais=row["numeroPais"],
        admitido=admitido,
        estadoRegistro=row["estadoRegistro"],
        categoria=row["categoria"],
        multaActiva=row["multaActiva"],
        bloqueado=row["bloqueado"],
    )


@router.patch("/me")
async def update_profile(
    nombre: Optional[str] = Form(None),
    apellido: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]

    # Fetch current user name
    with db.cursor() as cursor:
        cursor.execute("SELECT nombre, documento FROM personas WHERE identificador = %s", (user_id,))
        person = cursor.fetchone()
        if not person:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

    current_full_name = person["nombre"] or ""

    # Split name to override pieces
    parts = current_full_name.split(" ", 1)
    curr_nombre = parts[0]
    curr_apellido = parts[1] if len(parts) > 1 else ""

    new_nombre = nombre if nombre is not None else curr_nombre
    new_apellido = apellido if apellido is not None else curr_apellido
    new_full_name = f"{new_nombre} {new_apellido}".strip()

    # Update personas table
    with db.cursor() as cursor:
        if new_full_name:
            cursor.execute("UPDATE personas SET nombre = %s WHERE identificador = %s", (new_full_name, user_id))
        if direccion is not None:
            cursor.execute("UPDATE personas SET direccion = %s WHERE identificador = %s", (direccion, user_id))

        # Update personas_adicionales table
        if telefono is not None:
            cursor.execute("UPDATE personas_adicionales SET telefono = %s WHERE identificador = %s", (telefono, user_id))

        # Handle file upload
        if foto:
            foto_bytes = await foto.read()
            foto_url = StorageService.upload_file(
                foto_bytes,
                f"profile/{user_id}/photo.jpg",
                foto.content_type or "image/jpeg",
            )
            cursor.execute("UPDATE personas_adicionales SET foto_url = %s WHERE identificador = %s", (foto_url, user_id))

    db.commit()
    return {"message": "Perfil actualizado correctamente"}


@router.get("/me/medios-pago", response_model=list[MedioPago])
async def list_payment_methods(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                identificador as id,
                tipo,
                ultimos_digitos,
                estado_verificacion as "estadoVerificacion",
                moneda,
                limite_reservado as "limiteReservado",
                pais_banco as "paisBanco",
                es_cuenta_receptora as "esCuentaReceptora"
            FROM medios_pago
            WHERE cliente_id = %s
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            MedioPago(
                id=row["id"],
                tipo=row["tipo"],
                ultimos_digitos=row["ultimos_digitos"],
                estadoVerificacion=row["estadoVerificacion"],
                moneda=row["moneda"],
                limiteReservado=float(row["limiteReservado"] or 0),
                paisBanco=row["paisBanco"],
                esCuentaReceptora=bool(row["esCuentaReceptora"]),
            )
            for row in rows
        ]


@router.post("/me/medios-pago", status_code=201)
async def add_payment_method(
    body: MedioPagoInput,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]

    # Extract last 4 digits
    ultimos_digitos = "4321"
    if body.datos_encriptados:
        digits = [c for c in body.datos_encriptados if c.isdigit()]
        if len(digits) >= 4:
            ultimos_digitos = "".join(digits[-4:])
        else:
            ultimos_digitos = body.datos_encriptados[-4:]

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO medios_pago (
                cliente_id, tipo, datos_encriptados, ultimos_digitos,
                estado_verificacion, moneda, limite_reservado, pais_banco, es_cuenta_receptora
            ) VALUES (%s, %s, %s, %s, 'pendiente', %s, %s, %s, %s)
            """,
            (
                user_id,
                body.tipo.value,
                body.datos_encriptados,
                ultimos_digitos,
                body.moneda.value,
                body.limiteReservado or 0.00,
                body.paisBanco,
                body.esCuentaReceptora or False,
            ),
        )
    db.commit()
    return {"message": "Medio de pago agregado correctamente"}


@router.patch("/me/medios-pago/{id}")
async def update_payment_method(
    id: int,
    body: MedioPagoUpdate,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        cursor.execute("SELECT 1 FROM medios_pago WHERE identificador = %s AND cliente_id = %s", (id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

        updates = []
        params = []
        if body.limiteReservado is not None:
            updates.append("limite_reservado = %s")
            params.append(body.limiteReservado)
        if body.esCuentaReceptora is not None:
            updates.append("es_cuenta_receptora = %s")
            params.append(body.esCuentaReceptora)

        if not updates:
            return {"message": "No se realizaron cambios"}

        params.append(id)
        cursor.execute(f"UPDATE medios_pago SET {', '.join(updates)} WHERE identificador = %s", tuple(params))
    db.commit()
    return {"message": "Medio de pago actualizado"}


@router.delete("/me/medios-pago/{id}", status_code=204)
async def delete_payment_method(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        cursor.execute("SELECT 1 FROM medios_pago WHERE identificador = %s AND cliente_id = %s", (id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

        cursor.execute("DELETE FROM medios_pago WHERE identificador = %s", (id,))
    db.commit()


@router.get("/me/metricas", response_model=UsuarioMetricas)
async def get_metrics(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        # Get total subastas participadas
        cursor.execute("SELECT COUNT(DISTINCT subasta) as total FROM asistentes WHERE cliente = %s", (user_id,))
        total_participadas = cursor.fetchone()["total"] or 0

        # Get total subastas ganadas
        cursor.execute("SELECT COUNT(DISTINCT subasta) as total FROM registrodesubasta WHERE cliente = %s", (user_id,))
        total_ganadas = cursor.fetchone()["total"] or 0

        # Get total pujas realizadas
        cursor.execute(
            "SELECT COUNT(*) as total_pujas, COALESCE(SUM(importe), 0) as total_importe FROM pujos p JOIN asistentes a ON p.asistente = a.identificador WHERE a.cliente = %s",
            (user_id,)
        )
        pujas_row = cursor.fetchone()
        total_pujas = pujas_row["total_pujas"] or 0
        monto_ofertado = float(pujas_row["total_importe"] or 0)

        # Get total pagado
        cursor.execute("SELECT COALESCE(SUM(total_final), 0) as total FROM pagos WHERE cliente_id = %s AND estado = 'pagado'", (user_id,))
        total_pagado = float(cursor.fetchone()["total"] or 0)

        # Get porcentaje exito
        porcentaje_exito = 0.0
        if total_participadas > 0:
            porcentaje_exito = (total_ganadas / total_participadas) * 100.0

        # Get categorias participadas
        cursor.execute(
            "SELECT DISTINCT s.categoria FROM subastas s JOIN asistentes a ON s.identificador = a.subasta WHERE a.cliente = %s",
            (user_id,)
        )
        categorias = [row["categoria"] for row in cursor.fetchall() if row["categoria"] is not None]

        # Get ultima participacion
        cursor.execute("SELECT MAX(fecha_hora_inicio) as max_fecha FROM sesiones_subasta WHERE cliente_id = %s", (user_id,))
        ultima_participacion = cursor.fetchone()["max_fecha"]

        return UsuarioMetricas(
            totalSubastasParticipadas=total_participadas,
            totalSubastasGanadas=total_ganadas,
            porcentajeExito=porcentaje_exito,
            totalPujasRealizadas=total_pujas,
            montoTotalOfertado=monto_ofertado,
            montoTotalPagado=total_pagado,
            categoriasParticipadas=categorias,
            ultimaParticipacion=ultima_participacion
        )


@router.get("/me/multas", response_model=list[Multa])
async def list_fines(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                identificador as id,
                importe,
                estado,
                fecha_limite as "fechaLimite",
                motivo
            FROM multas
            WHERE cliente_id = %s
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            Multa(
                id=row["id"],
                importe=float(row["importe"]),
                estado=row["estado"],
                fechaLimite=row["fechaLimite"],
                motivo=row["motivo"],
            )
            for row in rows
        ]


@router.post("/me/multas/pagar")
async def pay_fine(
    body: MultaPagoRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["usuarioId"]
    with db.cursor() as cursor:
        # Verify fine ownership and status
        cursor.execute(
            "SELECT estado FROM multas WHERE identificador = %s AND cliente_id = %s",
            (body.multaId, user_id)
        )
        fine = cursor.fetchone()
        if not fine:
            raise HTTPException(status_code=404, detail="Multa no encontrada")
        if fine["estado"] == "pagada":
            raise HTTPException(status_code=400, detail="La multa ya está pagada")

        # Verify payment method ownership and status
        cursor.execute(
            "SELECT estado_verificacion FROM medios_pago WHERE identificador = %s AND cliente_id = %s",
            (body.medioPagoId, user_id)
        )
        payment_method = cursor.fetchone()
        if not payment_method:
            raise HTTPException(status_code=404, detail="Medio de pago no encontrado")
        if payment_method["estado_verificacion"] != "validado":
            raise HTTPException(status_code=400, detail="El medio de pago no está validado")

        # Perform payment
        cursor.execute(
            "UPDATE multas SET estado = 'pagada', medio_pago_id = %s WHERE identificador = %s",
            (body.medioPagoId, body.multaId)
        )

        # Check if there are any remaining pending fines
        cursor.execute(
            "SELECT 1 FROM multas WHERE cliente_id = %s AND estado = 'pendiente'",
            (user_id,)
        )
        remaining = cursor.fetchone()
        if not remaining:
            cursor.execute(
                "UPDATE clientes_adicionales SET multa_activa = false WHERE identificador = %s",
                (user_id,)
            )

    db.commit()
    return {"message": "Multa pagada correctamente"}

