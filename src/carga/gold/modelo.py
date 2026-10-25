"""Creación del modelo Gold a partir del SQL separado por responsabilidad."""
from pathlib import Path

ARCHIVOS_MODELO = ('dimensiones.sql', 'hechos.sql', 'auditoria.sql', 'vistas_gold.sql')


def crear_modelo(conexion):
    """Crea dimensiones, hechos, auditoría y vistas, en ese orden."""
    carpeta_sql = Path(__file__).resolve().parents[3] / 'sql'
    for nombre in ARCHIVOS_MODELO:
        esquema = (carpeta_sql / nombre).read_text(encoding='utf-8')
        for sentencia in esquema.split(';'):
            if sentencia.strip():
                conexion.exec_driver_sql(sentencia)
