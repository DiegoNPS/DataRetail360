"""Carga de las cuatro dimensiones antes de los hechos."""
from .insercion import cargar_tablas

DIMENSIONES = ('dim_fecha', 'dim_producto', 'dim_cliente', 'dim_sucursal_canal')


def cargar_dimensiones(conexion, tablas):
    """Inserta las dimensiones preparadas dentro de la transacción recibida."""
    cargar_tablas(conexion, tablas, DIMENSIONES)
