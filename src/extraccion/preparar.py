"""Coordinación de las siete fuentes; cada extractor se ocupa de su archivo."""
import pandas as pd
from .lector_csv import leer_manifiesto
from .sucursales import extraer_sucursales
from .productos import extraer_productos, extraer_cambios_producto
from .clientes import extraer_clientes, extraer_cambios_cliente
from .ventas import extraer_ventas
from .devoluciones import extraer_devoluciones


def extraer_fuentes(carpeta_entrada, id_ejecucion):
    """Reúne las tablas crudas, la auditoría de lectura y el manifiesto original."""
    manifiesto = leer_manifiesto(carpeta_entrada)
    extractores = (
        ('sucursales', extraer_sucursales),
        ('productos', extraer_productos),
        ('clientes', extraer_clientes),
        ('cambios_cliente', extraer_cambios_cliente),
        ('cambios_producto', extraer_cambios_producto),
        ('ventas', extraer_ventas),
        ('devoluciones', extraer_devoluciones),
    )
    fuentes = {}
    manifiesto_real = []
    for nombre, extraer in extractores:
        frame, registro = extraer(carpeta_entrada, manifiesto, id_ejecucion)
        fuentes[nombre] = frame
        manifiesto_real.append(registro)
    return fuentes, pd.DataFrame(manifiesto_real), manifiesto
