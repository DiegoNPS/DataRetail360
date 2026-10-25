"""Extracción independiente de devoluciones desde sus archivos Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_devoluciones(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente devoluciones.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'devoluciones', CONTRATOS['devoluciones'], manifiesto, id_ejecucion)
