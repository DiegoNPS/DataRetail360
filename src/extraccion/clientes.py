"""Extracción independiente de clientes, cambios_cliente desde sus archivos Bronze."""
from ..comun.contratos import CONTRATOS
from .lector_csv import leer_csv_validado


def extraer_clientes(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente clientes.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'clientes', CONTRATOS['clientes'], manifiesto, id_ejecucion)


def extraer_cambios_cliente(carpeta_entrada, manifiesto, id_ejecucion):
    """Extrae únicamente cambios_cliente.csv; conserva los valores crudos como texto."""
    return leer_csv_validado(carpeta_entrada, 'cambios_cliente', CONTRATOS['cambios_cliente'], manifiesto, id_ejecucion)
