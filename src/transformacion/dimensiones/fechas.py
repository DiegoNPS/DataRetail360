"""Calendario dimensional basado en las fechas de ventas y devoluciones aceptadas."""
import pandas as pd


def preparar_fechas(ventas_validas, devoluciones_validas):
    """Devuelve todos los días de los años cubiertos por los hechos válidos."""
    todas_fechas = list(ventas_validas.clave_fecha) + list(devoluciones_validas.clave_fecha)
    inicio = str(min(todas_fechas))[:4]
    fin = str(max(todas_fechas))[:4]
    calendario = pd.date_range(inicio + '-01-01', fin + '-12-31')
    dimension_fecha = pd.DataFrame(dict(clave_fecha=calendario.strftime('%Y%m%d').astype(int), fecha=calendario.strftime('%Y-%m-%d'), dia=calendario.day, mes=calendario.month, trimestre=calendario.quarter, anio=calendario.year))
    return dimension_fecha
