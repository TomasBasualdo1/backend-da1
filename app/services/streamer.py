"""
Gestor de eventos en tiempo real para subastas usando Server-Sent Events (SSE).
Mantiene colas asincronas por subasta para broadcast de pujas.
"""
import asyncio
import json
from datetime import datetime, timezone
from collections import defaultdict


class SubastaStreamer:
    """Singleton que gestiona las conexiones SSE por subasta."""

    _listeners: dict[int, list[asyncio.Queue]] = defaultdict(list)

    @classmethod
    def subscribe(cls, subasta_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        cls._listeners[subasta_id].append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, subasta_id: int, queue: asyncio.Queue) -> None:
        try:
            cls._listeners[subasta_id].remove(queue)
        except ValueError:
            pass
        if not cls._listeners[subasta_id]:
            del cls._listeners[subasta_id]

    @classmethod
    async def broadcast(cls, subasta_id: int, event_type: str, data: dict) -> None:
        event = {
            "type": event_type,
            "fechaHora": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        dead_queues = []
        for queue in cls._listeners.get(subasta_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            cls.unsubscribe(subasta_id, q)

    @classmethod
    async def generate_events(cls, subasta_id: int, queue: asyncio.Queue):
        """Generador asincrono que produce los eventos SSE."""
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            # Enviar keepalive y continuar
            yield f": keepalive\n\n"
        except asyncio.CancelledError:
            return
        finally:
            cls.unsubscribe(subasta_id, queue)
