from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from psycopg import Connection

from app.repositories.puja_repo import PujaRepository
from app.repositories.subasta_repo import SubastaRepository
from app.schemas.schemas import CatalogoItemInput, SubastaCreate


CATEGORIAS_PESO = {"comun": 1, "especial": 2, "plata": 3, "oro": 4, "platino": 5}
COSTO_ENVIO_SUBASTA = 500.0
MULTA_PORCENTAJE = 0.10


class SubastaService:

    # ─────────────────── LISTADOS ───────────────────

    @staticmethod
    def get_publicas(db: Connection) -> list[dict]:
        return SubastaRepository.get_publicas(db)

    @staticmethod
    def get_publica_detalle(
        db: Connection, subasta_id: int, base_url: str
    ) -> dict | None:
        return SubastaRepository.get_publica_detalle(db, subasta_id, base_url)

    @staticmethod
    def get_todas(db: Connection) -> list[dict]:
        return SubastaRepository.get_todas(db)

    @staticmethod
    def get_detalle(
        db: Connection,
        subasta_id: int,
        base_url: str,
        usuario_id: int,
        categoria_usuario: str,
    ) -> dict | None:
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        if not subasta:
            return None

        peso_subasta = CATEGORIAS_PESO.get(subasta["categoria"], 1)
        peso_usuario = CATEGORIAS_PESO.get(categoria_usuario, 1)
        if peso_usuario < peso_subasta:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu categoria no es suficiente para ver el detalle de esta subasta",
            )

        return SubastaRepository.get_detalle(db, subasta_id, base_url)

    # ─────────────────── ADMIN ───────────────────

    @staticmethod
    def create_subasta(
        db: Connection,
        subasta: SubastaCreate,
        usuario_id: int | None,
    ) -> dict:
        min_fecha = date.today() + timedelta(days=10)
        if subasta.fecha <= min_fecha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de la subasta debe ser posterior a 10 dias desde hoy.",
            )

        return SubastaRepository.create_subasta(db, subasta, usuario_id)

    @staticmethod
    def add_catalog_item(
        db: Connection,
        subasta_id: int,
        item: CatalogoItemInput,
        usuario_id: int | None,
    ) -> dict:
        has_producto = item.productoId is not None
        has_articulo = item.articuloId is not None
        if has_producto == has_articulo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe enviar exactamente uno de productoId o articuloId.",
            )

        if item.precioBase <= 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="precioBase debe ser mayor a 0.01.",
            )

        if item.comision <= 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comision debe ser mayor a 0.01.",
            )

        return SubastaRepository.add_catalog_item(db, subasta_id, item, usuario_id)

    # ─────────────────── PUJAS ───────────────────

    @staticmethod
    def _fecha_vencida(fecha_limite) -> bool:
        if not fecha_limite:
            return False

        if isinstance(fecha_limite, str):
            try:
                fecha_limite = datetime.fromisoformat(
                    fecha_limite.replace("Z", "+00:00")
                )
            except ValueError:
                return False

        if isinstance(fecha_limite, datetime):
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            return fecha_limite < datetime.now(timezone.utc)

        return False

    @staticmethod
    def procesar_vencimientos(
        db: Connection, usuario_id: int | None = None
    ) -> dict:
        try:
            pagos_vencidos = list(
                SubastaRepository.get_pagos_pendientes_vencidos(db, usuario_id)
                or []
            )
            multas_vencidas = list(
                SubastaRepository.get_multas_pendientes_vencidas(db, usuario_id)
                or []
            )

            pagos_procesados = 0
            multas_creadas = 0
            usuarios_multa_activa: set[int] = set()
            usuarios_bloqueados: set[int] = set()

            for pago in pagos_vencidos:
                pago_id = pago["id"]
                cliente_id = pago["usuarioId"]
                subasta_id = pago["subastaId"]
                total_pujado = float(pago["totalPujado"] or 0.0)
                motivo = f"Incumplimiento de pago #{pago_id} subasta #{subasta_id}"

                if SubastaRepository.marcar_pago_vencido(db, pago_id):
                    pagos_procesados += 1
                    SubastaRepository.crear_notificacion(
                        db,
                        cliente_id,
                        "pago",
                        f"El pago #{pago_id} de la subasta #{subasta_id} vencio.",
                    )

                multa, creada = SubastaRepository.generar_multa(
                    db,
                    cliente_id,
                    total_pujado,
                    motivo,
                )
                if multa.get("estado") == "pendiente":
                    usuarios_multa_activa.add(cliente_id)
                if creada:
                    multas_creadas += 1
                    SubastaRepository.crear_notificacion(
                        db,
                        cliente_id,
                        "sistema",
                        f"Se genero una multa del {int(MULTA_PORCENTAJE * 100)}% "
                        f"(${float(multa['importe']):.2f}) por el pago #{pago_id}.",
                    )

            for multa in multas_vencidas:
                cliente_id = multa["cliente_id"]
                if SubastaRepository.bloquear_usuario(db, cliente_id):
                    usuarios_bloqueados.add(cliente_id)
                    SubastaRepository.crear_notificacion(
                        db,
                        cliente_id,
                        "sistema",
                        "Tu usuario fue bloqueado por incumplimiento de obligaciones de pago.",
                    )

            if (
                pagos_procesados
                or multas_creadas
                or usuarios_multa_activa
                or usuarios_bloqueados
            ):
                db.commit()

            return {
                "pagosVencidosProcesados": pagos_procesados,
                "multasCreadas": multas_creadas,
                "usuariosMarcadosMultaActiva": sorted(usuarios_multa_activa),
                "usuariosBloqueados": sorted(usuarios_bloqueados),
                "multasVencidasBloqueantes": len(multas_vencidas),
            }
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _calcular_exposicion_con_puja(
        pagos_pendientes: float,
        pujas_ganadoras: list[dict],
        item_id: int,
        importe_candidato: float,
    ) -> tuple[float, float]:
        exposicion_actual = float(pagos_pendientes or 0.0)
        exposicion_con_candidata = float(pagos_pendientes or 0.0)
        reemplaza_item_actual = False

        for puja in pujas_ganadoras:
            puja_item_id = puja.get("itemId") or puja.get("item_id")
            importe_actual = float(puja.get("importe") or 0.0)
            exposicion_actual += importe_actual

            if puja_item_id == item_id:
                exposicion_con_candidata += float(importe_candidato)
                reemplaza_item_actual = True
            else:
                exposicion_con_candidata += importe_actual

        if not reemplaza_item_actual:
            exposicion_con_candidata += float(importe_candidato)

        return exposicion_actual, exposicion_con_candidata

    @staticmethod
    def _validar_garantia_para_puja(
        db: Connection,
        usuario_id: int,
        item_id: int,
        importe: float,
        moneda: str = "USD",
    ) -> None:
        garantia = SubastaRepository.get_garantia_validada_for_update(
            db,
            usuario_id,
            moneda,
        )
        garantia_total = float(garantia.get("total") or 0.0)

        if garantia_total <= 0:
            return

        pagos_pendientes = SubastaRepository.get_exposicion_pagos_pendientes(
            db,
            usuario_id,
            moneda,
        )
        pujas_ganadoras = SubastaRepository.get_pujas_ganadoras_parciales_activas(
            db,
            usuario_id,
        )
        exposicion_actual, exposicion_con_candidata = (
            SubastaService._calcular_exposicion_con_puja(
                pagos_pendientes,
                pujas_ganadoras,
                item_id,
                importe,
            )
        )

        if exposicion_con_candidata <= garantia_total:
            return

        garantia_disponible = max(garantia_total - exposicion_actual, 0.0)
        importe_requerido = max(exposicion_con_candidata - exposicion_actual, 0.0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "codigo": "GARANTIA_INSUFICIENTE",
                "mensaje": "La puja excede tu garantia disponible para compras pendientes.",
                "garantiaDisponible": round(garantia_disponible, 2),
                "exposicionActual": round(exposicion_actual, 2),
                "importeRequerido": round(importe_requerido, 2),
                "moneda": moneda,
            },
        )

    @staticmethod
    def procesar_puja(
        db: Connection,
        subasta_id: int,
        item_id: int,
        usuario_id: int,
        categoria_usuario: str,
        importe: float,
        idempotency_key: str | None = None,
    ) -> dict:
        SubastaService.procesar_vencimientos(db, usuario_id)
        if not SubastaRepository.puede_participar(db, usuario_id):
            raise HTTPException(
                status_code=403, detail="Usuario bloqueado o con multas pendientes"
            )

        idempotency_key = PujaRepository.normalize_idempotency_key(idempotency_key)
        idempotency_record_id = None

        try:
            if idempotency_key:
                idempotency_record = (
                    PujaRepository.lock_or_create_idempotency_record(
                        db,
                        usuario_id,
                        subasta_id,
                        item_id,
                        importe,
                        idempotency_key,
                    )
                )
                if idempotency_record:
                    if idempotency_record.get("_created"):
                        idempotency_record_id = idempotency_record["identificador"]
                    else:
                        if (
                            idempotency_record["subasta_id"] != subasta_id
                            or idempotency_record["item_id"] != item_id
                            or float(idempotency_record["importe"]) != float(importe)
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=(
                                    "Idempotency-Key ya fue usada con una puja distinta"
                                ),
                            )
                        if idempotency_record["estado"] == "completed":
                            response = PujaRepository.response_from_idempotency_record(
                                idempotency_record
                            )
                            db.commit()
                            return response
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Puja con la misma Idempotency-Key en proceso",
                        )

            asistente_id = SubastaRepository.get_asistente_id(
                db, subasta_id, usuario_id
            )
            if not asistente_id:
                raise HTTPException(
                    status_code=403,
                    detail="Debes unirte a la subasta para poder pujar",
                )

            item = SubastaRepository.get_item_for_update(db, subasta_id, item_id)
            if not item:
                raise HTTPException(
                    status_code=404, detail="Ítem no encontrado en esta subasta"
                )

            if item.get("subastado") == "si":
                raise HTTPException(
                    status_code=400, detail="Este ítem ya fue subastado"
                )

            precio_base = float(item["preciobase"])
            mejor_oferta_actual = SubastaRepository.get_mejor_oferta(db, item_id)

            if mejor_oferta_actual == 0.0:
                limite_minimo = precio_base
                limite_maximo = precio_base + (precio_base * 0.20)
            else:
                limite_minimo = mejor_oferta_actual + (precio_base * 0.01)
                limite_maximo = mejor_oferta_actual + (precio_base * 0.20)

            subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
            categoria_subasta = subasta["categoria"] if subasta else "comun"
            es_subasta_premium = categoria_subasta in ("oro", "platino")

            if not es_subasta_premium:
                if importe < limite_minimo:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La puja mínima es de ${limite_minimo:.2f} "
                            "(mejor oferta + 1% del valor base)"
                        ),
                    )
                if importe > limite_maximo:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La puja máxima permitida es de ${limite_maximo:.2f} "
                            "(mejor oferta + 20% del valor base)"
                        ),
                    )
            else:
                if mejor_oferta_actual == 0.0 and importe < precio_base:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La puja inicial debe ser al menos el precio base "
                            f"(${precio_base:.2f})"
                        ),
                    )
                if mejor_oferta_actual > 0.0 and importe <= mejor_oferta_actual:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La puja debe superar la oferta actual "
                            f"(${mejor_oferta_actual:.2f})"
                        ),
                    )

            SubastaService._validar_garantia_para_puja(
                db,
                usuario_id,
                item_id,
                importe,
                "USD",
            )

            puja_id = SubastaRepository.registrar_puja(
                db, asistente_id, item_id, importe
            )

            nuevo_limite_minimo = importe + (precio_base * 0.01)
            nuevo_limite_maximo = importe + (precio_base * 0.20)

            response = {
                "pujaId": puja_id,
                "mejorOfertaActual": importe,
                "limiteMinimo": nuevo_limite_minimo,
                "limiteMaximo": nuevo_limite_maximo,
                "moneda": "USD",
                "esGanadoraParcial": True,
            }

            if idempotency_record_id is not None:
                PujaRepository.mark_idempotency_completed(
                    db, idempotency_record_id, response
                )

            db.commit()

            return response
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    # ─────────────────── JOIN / LEAVE ───────────────────

    @staticmethod
    def join_subasta(
        db: Connection, subasta_id: int, usuario_id: int, categoria_usuario: str
    ):
        SubastaService.procesar_vencimientos(db, usuario_id)
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        if not subasta:
            raise HTTPException(status_code=404, detail="Subasta no encontrada")

        if subasta["estado"] != "abierta":
            raise HTTPException(status_code=400, detail="La subasta no está abierta")

        peso_subasta = CATEGORIAS_PESO.get(subasta["categoria"], 1)
        peso_usuario = CATEGORIAS_PESO.get(categoria_usuario, 1)

        if peso_usuario < peso_subasta:
            raise HTTPException(
                status_code=403,
                detail="Tu categoría no es suficiente para participar en esta subasta",
            )

        if not SubastaRepository.puede_participar(db, usuario_id):
            raise HTTPException(
                status_code=403, detail="Usuario bloqueado o con multas pendientes"
            )

        if not SubastaRepository.tiene_medio_pago_validado(db, usuario_id):
            raise HTTPException(
                status_code=403,
                detail="Debes tener al menos un medio de pago validado para participar",
            )

        if SubastaRepository.check_otra_sesion_activa(db, subasta_id, usuario_id):
            raise HTTPException(
                status_code=409,
                detail="Ya te encuentras conectado a otra subasta",
            )

        SubastaRepository.join_subasta(db, subasta_id, usuario_id)
        db.commit()
        return {"message": "Te has unido a la subasta exitosamente"}

    @staticmethod
    def leave_subasta(db: Connection, subasta_id: int, usuario_id: int):
        SubastaRepository.leave_subasta(db, subasta_id, usuario_id)
        db.commit()
        return {"message": "Has salido de la subasta"}

    @staticmethod
    def validar_acceso_stream(
        db: Connection,
        subasta_id: int,
        usuario_id: int,
        categoria_usuario: str,
    ) -> None:
        SubastaService.procesar_vencimientos(db, usuario_id)
        subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
        if not subasta:
            raise HTTPException(status_code=404, detail="Subasta no encontrada")

        if subasta["estado"] != "abierta":
            raise HTTPException(status_code=400, detail="La subasta no está abierta")

        peso_subasta = CATEGORIAS_PESO.get(subasta["categoria"], 1)
        peso_usuario = CATEGORIAS_PESO.get(categoria_usuario, 1)
        if peso_usuario < peso_subasta:
            raise HTTPException(
                status_code=403,
                detail="Tu categoría no es suficiente para participar en esta subasta",
            )

        if not SubastaRepository.puede_participar(db, usuario_id):
            raise HTTPException(
                status_code=403, detail="Usuario bloqueado o con multas pendientes"
            )

        if not SubastaRepository.tiene_medio_pago_validado(db, usuario_id):
            raise HTTPException(
                status_code=403,
                detail="Debes tener al menos un medio de pago validado para participar",
            )

        if not SubastaRepository.tiene_sesion_activa(db, subasta_id, usuario_id):
            raise HTTPException(
                status_code=403,
                detail="Debes unirte a la subasta para recibir actualizaciones en vivo",
            )

    # ─────────────────── CIERRE ───────────────────

    @staticmethod
    def cerrar_subasta(db: Connection, subasta_id: int):
        try:
            subasta = SubastaRepository.get_subasta_basica(db, subasta_id)
            if not subasta:
                raise HTTPException(status_code=404, detail="Subasta no encontrada")
            if subasta["estado"] == "cerrada":
                raise HTTPException(status_code=400, detail="La subasta ya está cerrada")

            items = SubastaRepository.obtener_items_con_pujas(db, subasta_id)
            pagos_por_cliente: dict[int, dict] = defaultdict(
                lambda: {"total_pujado": 0.0, "comision": 0.0}
            )

            for item in items:
                item_id = item["item_id"]
                precio_base = float(item["preciobase"])
                comision_item = float(item["comision"])
                producto_id = item["producto"]
                duenio_id = item["duenio"]

                if item["puja_id"]:
                    cliente_ganador = item["cliente_ganador"]
                    importe_final = float(item["puja_importe"])

                    SubastaRepository.cerrar_item(db, item_id, item["puja_id"])
                    SubastaRepository.registrar_venta(
                        db,
                        subasta_id,
                        duenio_id,
                        producto_id,
                        cliente_ganador,
                        importe_final,
                        comision_item,
                    )

                    pagos_por_cliente[cliente_ganador]["total_pujado"] += importe_final
                    pagos_por_cliente[cliente_ganador]["comision"] += comision_item

                    SubastaRepository.crear_notificacion(
                        db,
                        cliente_ganador,
                        "subasta",
                        f"Ganaste el item #{item_id} por ${importe_final:.2f}. "
                        f"Comision: ${comision_item:.2f}. Tenes 72hs para abonar.",
                    )
                else:
                    SubastaRepository.cerrar_item(db, item_id, None)
                    SubastaRepository.crear_notificacion(
                        db,
                        duenio_id,
                        "subasta",
                        f"Tu articulo #{producto_id} fue adquirido por la empresa al precio base (${precio_base:.2f}).",
                    )

            for cliente_id, totales in pagos_por_cliente.items():
                SubastaRepository.generar_pago(
                    db,
                    subasta_id,
                    cliente_id,
                    totales["total_pujado"],
                    totales["comision"],
                    "USD",
                )

            SubastaRepository.marcar_subasta_cerrada(db, subasta_id)
            SubastaRepository.finalizar_sesiones(db, subasta_id)
            db.commit()

            return {
                "message": "Subasta cerrada exitosamente",
                "itemsCerrados": len(items),
                "pagosGenerados": len(pagos_por_cliente),
            }
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    # ─────────────────── HISTORIAL ───────────────────

    @staticmethod
    def get_historial(db: Connection, subasta_id: int, usuario_id: int) -> list[dict]:
        asistente_id = SubastaRepository.get_asistente_id(db, subasta_id, usuario_id)
        if not asistente_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debes unirte a la subasta para ver el historial de pujas",
            )
        return SubastaRepository.get_historial_pujas(db, subasta_id)

    # ─────────────────── PAGOS ───────────────────

    @staticmethod
    def get_pago(db: Connection, subasta_id: int, usuario_id: int) -> dict:
        SubastaService.procesar_vencimientos(db, usuario_id)
        pago = SubastaRepository.get_pago_usuario(db, subasta_id, usuario_id)
        if not pago:
            raise HTTPException(
                status_code=404,
                detail="No tenés pagos pendientes en esta subasta",
            )
        return pago

    @staticmethod
    def confirmar_pago(
        db: Connection,
        subasta_id: int,
        usuario_id: int,
        medio_pago_id: int,
        modo_entrega: str,
        direccion_envio: str | None,
        acepta_perder_seguro: bool,
    ):
        try:
            pago = SubastaRepository.get_pago_usuario(db, subasta_id, usuario_id)
            if not pago:
                raise HTTPException(
                    status_code=404,
                    detail="No tenes pagos pendientes en esta subasta",
                )

            if pago["estado"] == "pagado":
                raise HTTPException(status_code=400, detail="El pago ya fue realizado")

            if pago["estado"] != "pendiente":
                raise HTTPException(
                    status_code=409,
                    detail="El pago no se encuentra pendiente",
                )

            if SubastaService._fecha_vencida(pago.get("fechaLimitePago")):
                SubastaService.procesar_vencimientos(db, usuario_id)
                raise HTTPException(
                    status_code=409,
                    detail="El pago se encuentra vencido",
                )

            if modo_entrega not in ("envio", "retiro"):
                raise HTTPException(status_code=400, detail="Modo de entrega invalido")

            direccion_normalizada = direccion_envio.strip() if direccion_envio else None
            if modo_entrega == "envio" and not direccion_normalizada:
                raise HTTPException(
                    status_code=400,
                    detail="La direccion de envio es obligatoria",
                )

            if modo_entrega == "retiro":
                if not acepta_perder_seguro:
                    raise HTTPException(
                        status_code=400,
                        detail="Debe aceptar la perdida de seguro para retirar",
                    )
                direccion_normalizada = None
                acepta_perder_seguro = True

            medio = SubastaRepository.get_medio_pago_para_cliente(
                db,
                usuario_id,
                medio_pago_id,
            )
            if not medio:
                raise HTTPException(
                    status_code=403,
                    detail="Medio de pago no autorizado para este usuario",
                )

            if medio["estado_verificacion"] != "validado":
                raise HTTPException(
                    status_code=403,
                    detail="Medio de pago no validado",
                )

            if medio["moneda"] != pago["moneda"]:
                raise HTTPException(
                    status_code=400,
                    detail="Moneda invalida para este pago",
                )

            costo_envio = COSTO_ENVIO_SUBASTA if modo_entrega == "envio" else 0.0
            total_final = float(pago["totalPujado"]) + float(pago["comision"]) + costo_envio
            limite_reservado = float(medio["limite_reservado"] or 0.0)
            if limite_reservado > 0 and limite_reservado < total_final:
                raise HTTPException(status_code=400, detail="Fondos insuficientes")

            SubastaRepository.confirmar_pago(
                db,
                pago["id"],
                medio_pago_id,
                modo_entrega,
                direccion_normalizada,
                acepta_perder_seguro,
                costo_envio,
                total_final,
            )

            SubastaRepository.crear_notificacion(
                db,
                usuario_id,
                "pago",
                f"Pago confirmado por ${total_final:.2f} para la subasta #{subasta_id}. "
                f"Modo de entrega: {modo_entrega}.",
            )
            db.commit()

            return {"message": "Pago confirmado exitosamente"}
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
