"""Carga de hechos: primero ventas, después sus eventos de devolución."""
from .insercion import cargar_tablas

HECHOS = ('hecho_ventas', 'hecho_devoluciones')


def cargar_hechos(conexion, tablas):
    """Conserva el orden que exige la referencia de devoluciones a ventas."""
    cargar_tablas(conexion, tablas, HECHOS)
