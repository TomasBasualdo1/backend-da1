import sys
import os
from dotenv import load_dotenv

# Asegurar que el directorio raíz del proyecto esté en el PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cargar variables de entorno antes de importar la configuración
load_dotenv()

from app.core.database import get_db_connection

def clear_all_subastas():
    print("=== LIMPIEZA DE SUBASTAS ===")
    print("Este script eliminará todas las subastas, catálogos, pujas y registros relacionados.")
    print("IMPORTANTE: Los productos, fotos, usuarios y dueños NO serán eliminados.")
    print("Los productos simplemente serán desvinculados de los catálogos.")
    print("============================")
    
    confirm = input("¿Estás seguro de que deseas continuar? (s/N): ")
    if confirm.strip().lower() != 's':
        print("Operación cancelada.")
        return

    queries = [
        ("1. Eliminando llaves de idempotencia de pujas...", "DELETE FROM public.puja_idempotency_keys;"),
        ("2. Eliminando pujas...", "DELETE FROM public.pujos;"),
        ("3. Eliminando asistentes...", "DELETE FROM public.asistentes;"),
        ("4. Eliminando registro histórico de subastas...", "DELETE FROM public.registrodesubasta;"),
        ("5. Eliminando pagos asociados a subastas...", "DELETE FROM public.pagos;"),
        ("6. Eliminando sesiones de subasta...", "DELETE FROM public.sesiones_subasta;"),
        ("7. Desvinculando productos de catálogos (eliminando items)...", "DELETE FROM public.itemscatalogo;"),
        ("8. Eliminando catálogos...", "DELETE FROM public.catalogos;"),
        ("9. Eliminando subastas...", "DELETE FROM public.subastas;")
    ]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for msg, sql in queries:
                    print(msg)
                    cur.execute(sql)
                conn.commit()
        print("\n¡Éxito! Todas las subastas y dependencias han sido eliminadas.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error al ejecutar la limpieza: {e}")
        print("Se ha realizado un ROLLBACK automático. No se modificó ningún dato en la base.")

if __name__ == "__main__":
    clear_all_subastas()
