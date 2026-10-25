"""Extracción independiente de ventas desde sus archivos Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_ventas(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente ventas.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'ventas', CONTRATOS['ventas'], manifiesto, id_ejecucion)
