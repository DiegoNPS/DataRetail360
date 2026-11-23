"""Carga de hechos: ventas, devoluciones y snapshot de stock."""
from .insercion import cargar_tablas

HECHOS = ('hecho_ventas', 'hecho_devoluciones', 'hecho_stock_diario')


def cargar_hechos(conexion, tablas):
    """Conserva el orden que exige la referencia de devoluciones a ventas."""
    cargar_tablas(conexion, tablas, HECHOS)
