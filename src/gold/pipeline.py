"""Coordina la construcción Gold sin mezclar dimensiones y hechos."""
from .dimensiones import (
    construir_dim_cliente, construir_dim_fecha, construir_dim_producto,
    construir_dim_sucursal,
)
from .hechos import construir_hecho_devoluciones, construir_hecho_ventas


def construir_dimensiones_gold(tablas_silver):
    productos, cambios = construir_dim_producto(
        tablas_silver["productos_limpios"], tablas_silver["cambios_producto_limpios"]
    )
    clientes = construir_dim_cliente(
        tablas_silver["clientes_limpios"], tablas_silver["cambios_cliente_limpios"]
    )
    sucursales = construir_dim_sucursal(tablas_silver["sucursales_limpias"])
    fechas = construir_dim_fecha(
        tablas_silver["ventas_limpias"], tablas_silver["devoluciones_limpias"]
    )
    return {"dim_fecha": fechas, "dim_producto": productos, "dim_cliente": clientes,
            "dim_sucursal_canal": sucursales}, cambios


def construir_hechos_gold(tablas_silver, dimensiones, id_ejecucion):
    ventas = construir_hecho_ventas(
        tablas_silver["ventas_limpias"], dimensiones["dim_producto"],
        dimensiones["dim_cliente"], dimensiones["dim_sucursal_canal"], id_ejecucion,
    )
    devoluciones = construir_hecho_devoluciones(
        tablas_silver["devoluciones_limpias"], ventas, id_ejecucion
    )
    return {"hecho_ventas": ventas, "hecho_devoluciones": devoluciones}
