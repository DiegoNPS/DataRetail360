"""Extracción independiente de sucursales desde sus archivos Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_sucursales(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente sucursales.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'sucursales', CONTRATOS['sucursales'], manifiesto, id_ejecucion)
