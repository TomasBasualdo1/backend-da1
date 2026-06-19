from collections import defaultdict

from fastapi import HTTPException
from psycopg import Connection

from app.repositories.subasta_repo import SubastaRepository
from app.services.streamer import SubastaStreamer


CATEGORIAS_PESO = {"comun": 1, "especial": 2, "plata": 3, "oro": 4, "platino": 5}


class SubastaService:

    # ─────────────────── LISTADOS ───────────────────

    @staticmethod
    def get_publicas(db: Connection) -> list[dict]:
        return SubastaRepository.get_publicas(db)

    @staticmethod
    def get_publica_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        return SubastaRepository.get_publica_detalle(db, subasta_id, base_url)

    @staticmethod
    def get_todas(db: Connection) -> list[dict]:
        return SubastaRepository.get_todas(db)

    @staticmethod
    def get_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        return SubastaRepository.get_detalle(db, subasta_id, base_url)

    # ─────────────────── PUJAS ───────────────────

    @staticmethod
    def procesar_puja(
        db: Connection,
        subasta_id: int,
        item_id: int,
        usuario_id: int,
        categoria_usuario: str,
        importe: float,
    ) -> dict:
        # 1. Verificar que el usuario es asistente de la subasta
        asistente_id = SubastaRepository.get_asistente_id(db, subasta_id, usuario_id)
        if not asistente_id:
            raise HTTPException(status_code=403, detail="Debes unirte a la subasta para poder pujar")

        # 2. Bloquear el item (FOR UPDATE) para evitar condiciones de carrera
        item = SubastaRepository.get_item_for_update(db, subasta_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Ítem no encontrado en esta subasta")

        if item.get("subastado") == "si":
            raise HTTPException(status_code=400, detail="Este ítem ya fue subastado")

        precio_base = float(item["preciobase"])

        # 3. Obtener la mejor oferta actual
        mejor_oferta_actual = SubastaRepository.get_mejor_oferta(db, item_id)

        # 4. Calcular limites segun regla de negocio
        if mejor_oferta_actual == 0.0:
            limite_minimo = precio_base
            limite_maximo = precio_base + (precio_base * 0.20)
        else:
            limite_minimo = mejor_oferta_actual + (precio_base * 0.01)
            limite_maximo = mejor_oferta_actual + (precio_base * 0.20)

        # 5. Validar segun categoria
        # Los limites del 1% y 20% NO aplican a subastas de categorias oro y platino
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        categoria_subasta = subasta["categoria"] if subasta else "comun"
        es_subasta_premium = categoria_subasta in ("oro", "platino")

        if not es_subasta_premium:
            if importe < limite_minimo:
                raise HTTPException(
                    status_code=400,
                    detail=f"La puja mínima es de ${limite_minimo:.2f} (mejor oferta + 1% del valor base)",
                )
            if importe > limite_maximo:
                raise HTTPException(
                    status_code=400,
                    detail=f"La puja máxima permitida es de ${limite_maximo:.2f} (mejor oferta + 20% del valor base)",
                )
        else:
            # En subastas premium solo se exige superar la oferta actual o el precio base
            if mejor_oferta_actual == 0.0 and importe < precio_base:
                raise HTTPException(status_code=400, detail=f"La puja inicial debe ser al menos el precio base (${precio_base:.2f})")
            if mejor_oferta_actual > 0.0 and importe <= mejor_oferta_actual:
                raise HTTPException(status_code=400, detail=f"La puja debe superar la oferta actual (${mejor_oferta_actual:.2f})")

        # 6. Registrar la puja
        puja_id = SubastaRepository.registrar_puja(db, asistente_id, item_id, importe)

        # 7. Calcular nuevos limites para la proxima puja
        nuevo_limite_minimo = importe + (precio_base * 0.01)
        nuevo_limite_maximo = importe + (precio_base * 0.20)

        db.commit()

        return {
            "pujaId": puja_id,
            "mejorOfertaActual": importe,
            "limiteMinimo": nuevo_limite_minimo,
            "limiteMaximo": nuevo_limite_maximo,
            "moneda": "USD",
            "esGanadoraParcial": True,
        }

    # ─────────────────── JOIN / LEAVE ───────────────────

    @staticmethod
    def join_subasta(db: Connection, subasta_id: int, usuario_id: int, categoria_usuario: str):
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        if not subasta:
            raise HTTPException(status_code=404, detail="Subasta no encontrada")

        if subasta["estado"] != "abierta":
            raise HTTPException(status_code=400, detail="La subasta no está abierta")

        peso_subasta = CATEGORIAS_PESO.get(subasta["categoria"], 1)
        peso_usuario = CATEGORIAS_PESO.get(categoria_usuario, 1)

        if peso_usuario < peso_subasta:
            raise HTTPException(status_code=403, detail="Tu categoría no es suficiente para participar en esta subasta")

        if not SubastaRepository.puede_participar(db, usuario_id):
            raise HTTPException(status_code=403, detail="Usuario bloqueado o con multas pendientes")

        if not SubastaRepository.tiene_medio_pago_validado(db, usuario_id):
            raise HTTPException(status_code=403, detail="Debes tener al menos un medio de pago validado para participar")

        if SubastaRepository.check_otra_sesion_activa(db, subasta_id, usuario_id):
            raise HTTPException(status_code=409, detail="Ya te encuentras conectado a otra subasta")

        SubastaRepository.join_subasta(db, subasta_id, usuario_id)
        db.commit()
        return {"message": "Te has unido a la subasta exitosamente"}

    @staticmethod
    def leave_subasta(db: Connection, subasta_id: int, usuario_id: int):
        SubastaRepository.leave_subasta(db, subasta_id, usuario_id)
        db.commit()
        return {"message": "Has salido de la subasta"}

    # ─────────────────── CIERRE ───────────────────

    @staticmethod
    def cerrar_subasta(db: Connection, subasta_id: int):
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        if not subasta:
            raise HTTPException(status_code=404, detail="Subasta no encontrada")
        if subasta["estado"] == "cerrada":
            raise HTTPException(status_code=400, detail="La subasta ya está cerrada")

        items = SubastaRepository.obtener_items_con_pujas(db, subasta_id)

        # Acumular pagos por cliente
        pagos_por_cliente: dict[int, dict] = defaultdict(lambda: {"total_pujado": 0.0, "comision": 0.0})

        for item in items:
            item_id = item["item_id"]
            precio_base = float(item["preciobase"])
            comision_item = float(item["comision"])
            producto_id = item["producto"]
            duenio_id = item["duenio"]

            if item["puja_id"]:
                # Hay un ganador
                cliente_ganador = item["cliente_ganador"]
                importe_final = float(item["puja_importe"])

                SubastaRepository.cerrar_item(db, item_id, item["puja_id"])
                SubastaRepository.registrar_venta(
                    db, subasta_id, duenio_id, producto_id, cliente_ganador, importe_final, comision_item,
                )

                pagos_por_cliente[cliente_ganador]["total_pujado"] += importe_final
                pagos_por_cliente[cliente_ganador]["comision"] += comision_item

                SubastaRepository.crear_notificacion(
                    db, cliente_ganador, "subasta",
                    f"¡Felicidades! Ganaste el ítem #{item_id} por ${importe_final:.2f}. "
                    f"Comisión: ${comision_item:.2f}. Tenés 72hs para abonar.",
                )
            else:
                # Nadie pujó → la empresa compra al precio base (consigna)
                SubastaRepository.cerrar_item(db, item_id, None)

                SubastaRepository.crear_notificacion(
                    db, duenio_id, "subasta",
                    f"Tu artículo #{producto_id} fue adquirido por la empresa al precio base (${precio_base:.2f}).",
                )

        # Generar pagos consolidados por cliente
        for cliente_id, totales in pagos_por_cliente.items():
            SubastaRepository.generar_pago(
                db, subasta_id, cliente_id, totales["total_pujado"], totales["comision"], "USD",
            )

        SubastaRepository.marcar_subasta_cerrada(db, subasta_id)
        SubastaRepository.finalizar_sesiones(db, subasta_id)
        db.commit()

        return {
            "message": "Subasta cerrada exitosamente",
            "itemsCerrados": len(items),
            "pagosGenerados": len(pagos_por_cliente),
        }

    # ─────────────────── HISTORIAL ───────────────────

    @staticmethod
    def get_historial(db: Connection, subasta_id: int, usuario_id: int) -> list[dict]:
        return SubastaRepository.get_historial_pujas(db, subasta_id, usuario_id)

    # ─────────────────── PAGOS ───────────────────

    @staticmethod
    def get_pago(db: Connection, subasta_id: int, usuario_id: int) -> dict:
        pago = SubastaRepository.get_pago_usuario(db, subasta_id, usuario_id)
        if not pago:
            raise HTTPException(status_code=404, detail="No tenés pagos pendientes en esta subasta")
        return pago

    @staticmethod
    def confirmar_pago(db: Connection, subasta_id: int, usuario_id: int, medio_pago_id: int, modo_entrega: str, direccion_envio: str | None, acepta_perder_seguro: bool):
        pago = SubastaRepository.get_pago_usuario(db, subasta_id, usuario_id)
        if not pago:
            raise HTTPException(status_code=404, detail="No tenés pagos pendientes en esta subasta")

        if pago["estado"] == "pagado":
            raise HTTPException(status_code=400, detail="El pago ya fue realizado")

        # Validar que el medio de pago le pertenece y esta validado
        if not SubastaRepository.tiene_medio_pago_validado(db, usuario_id):
            raise HTTPException(status_code=403, detail="No tenés un medio de pago validado")

        if modo_entrega == "retiro":
            acepta_perder_seguro = True

        SubastaRepository.confirmar_pago(db, pago["id"], medio_pago_id, modo_entrega, direccion_envio, acepta_perder_seguro)
        db.commit()

        SubastaRepository.crear_notificacion(
            db, usuario_id, "pago",
            f"Pago confirmado por ${pago['totalFinal']:.2f} para la subasta #{subasta_id}. "
            f"Modo de entrega: {modo_entrega}.",
        )
        db.commit()

        return {"message": "Pago confirmado exitosamente"}
