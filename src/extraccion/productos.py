"""Extracción independiente de productos, cambios_producto desde sus archivos Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_productos(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente productos.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'productos', CONTRATOS['productos'], manifiesto, id_ejecucion)


def extraer_cambios_producto(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente cambios_producto.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'cambios_producto', CONTRATOS['cambios_producto'], manifiesto, id_ejecucion)
