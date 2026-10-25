"""Coordina Silver sin mezclar reglas específicas de cada entidad."""
from .clientes import limpiar_clientes
from .devoluciones import limpiar_devoluciones
from .productos import limpiar_productos
from .sucursales import limpiar_sucursales
from .ventas import limpiar_ventas


def preparar_tablas_silver(contexto):
    """Ejecuta las transformaciones Silver en su orden de dependencia."""
    clientes, cambios_cliente = limpiar_clientes(contexto)
    productos, cambios_producto = limpiar_productos(contexto)
    sucursales = limpiar_sucursales(contexto)
    ventas = limpiar_ventas(contexto, sucursales, productos, clientes, cambios_cliente)
    devoluciones = limpiar_devoluciones(contexto, ventas)
    return {
        "clientes_limpios": clientes,
        "cambios_cliente_limpios": cambios_cliente,
        "productos_limpios": productos,
        "cambios_producto_limpios": cambios_producto,
        "sucursales_limpias": sucursales,
        "ventas_limpias": ventas,
        "devoluciones_limpias": devoluciones,
    }
