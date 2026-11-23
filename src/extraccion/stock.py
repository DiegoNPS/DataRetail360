"""Extracción del snapshot de stock de tiendas desde Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_stock_diario(carpeta_entrada, manifiesto, id_ejecucion):
    """Lee stock_diario.csv como texto sin aplicar reglas de negocio."""
    return leer_csv_validado(
        carpeta_entrada,
        "stock_diario",
        CONTRATOS["stock_diario"],
        manifiesto,
        id_ejecucion,
    )
