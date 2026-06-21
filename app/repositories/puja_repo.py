from fastapi import HTTPException, status
from psycopg import Connection


class PujaRepository:
    @staticmethod
    def normalize_idempotency_key(idempotency_key: str | None) -> str | None:
        if idempotency_key is None:
            return None

        normalized = idempotency_key.strip()
        if not normalized:
            return None

        if len(normalized) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key no puede superar 255 caracteres",
            )

        return normalized

    @staticmethod
    def lock_or_create_idempotency_record(
        db: Connection,
        cliente_id: int,
        subasta_id: int,
        item_id: int,
        importe: float,
        idempotency_key: str,
    ) -> dict | None:
        existing = PujaRepository.get_idempotency_record_for_update(
            db, cliente_id, idempotency_key
        )
        if existing:
            return existing

        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO puja_idempotency_keys (
                    cliente_id, subasta_id, item_id, importe, idempotency_key, estado
                )
                VALUES (%s, %s, %s, %s, %s, 'processing')
                ON CONFLICT (cliente_id, idempotency_key) DO NOTHING
                RETURNING identificador
                """,
                (cliente_id, subasta_id, item_id, importe, idempotency_key),
            )
            created = cursor.fetchone()

        if created:
            return {"identificador": created["identificador"], "_created": True}

        return PujaRepository.get_idempotency_record_for_update(
            db, cliente_id, idempotency_key
        )

    @staticmethod
    def get_idempotency_record_for_update(
        db: Connection,
        cliente_id: int,
        idempotency_key: str,
    ) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador,
                    cliente_id,
                    subasta_id,
                    item_id,
                    importe,
                    idempotency_key,
                    estado,
                    puja_id,
                    mejor_oferta_actual,
                    limite_minimo,
                    limite_maximo,
                    moneda,
                    es_ganadora_parcial
                FROM puja_idempotency_keys
                WHERE cliente_id = %s AND idempotency_key = %s
                FOR UPDATE
                """,
                (cliente_id, idempotency_key),
            )
            return cursor.fetchone()

    @staticmethod
    def mark_idempotency_completed(
        db: Connection,
        record_id: int,
        response: dict,
    ) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE puja_idempotency_keys
                SET
                    estado = 'completed',
                    puja_id = %s,
                    mejor_oferta_actual = %s,
                    limite_minimo = %s,
                    limite_maximo = %s,
                    moneda = %s,
                    es_ganadora_parcial = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE identificador = %s
                """,
                (
                    response["pujaId"],
                    response["mejorOfertaActual"],
                    response["limiteMinimo"],
                    response["limiteMaximo"],
                    response["moneda"],
                    response["esGanadoraParcial"],
                    record_id,
                ),
            )

    @staticmethod
    def response_from_idempotency_record(record: dict) -> dict:
        return {
            "pujaId": record["puja_id"],
            "mejorOfertaActual": float(record["mejor_oferta_actual"]),
            "limiteMinimo": float(record["limite_minimo"]),
            "limiteMaximo": float(record["limite_maximo"]),
            "moneda": record["moneda"],
            "esGanadoraParcial": bool(record["es_ganadora_parcial"]),
            "_idempotentReplay": True,
        }
