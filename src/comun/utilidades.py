"""Funciones puras de fechas, importes, claves y huellas SHA-256."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def ahora():
    return datetime.now(timezone.utc).isoformat()

def huella_archivo(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()

def fecha_valida(valor):
    try:
        return datetime.strptime(str(valor), '%Y-%m-%d').strftime('%Y-%m-%d') == valor
    except (ValueError, TypeError):
        return False

def es_entero(valor):
    try:
        return pd.notna(valor) and float(valor).is_integer()
    except (ValueError, TypeError):
        return False

def importe_con_descuento(gross, discount):
    return (int(gross) * (100 - int(discount)) + 50) // 100

def importe_proporcional(net, cantidad_previa, total):
    return (int(net) * int(cantidad_previa) + int(total) // 2) // int(total)

def clave_de_venta(fila):
    return f'{fila.sistema_origen}|{fila.id_comprobante}|{fila.numero_linea}'
