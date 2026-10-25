"""Limpieza y validación de la dimensión de sucursales y canales."""
import pandas as pd
from ...comun.dominios import REGIONES


def preparar_sucursales(contexto):
    """Devuelve sucursales con claves, canal y ubicación validados."""
    fuentes = contexto.fuentes
    conciliar = contexto.conciliar
    sucursales_dimension = fuentes['sucursales'].copy()
    sucursales_dimension['codigo_sucursal'] = sucursales_dimension.codigo_sucursal.str.strip().str.upper()
    columnas = ['codigo_sucursal', 'nombre_sucursal', 'canal', 'pais']
    if sucursales_dimension[columnas].eq('').any().any():
        raise ValueError('sucursales: campo obligatorio vacio')
    if sucursales_dimension.codigo_sucursal.duplicated().any():
        raise ValueError('Clave maestra duplicada')
    if not sucursales_dimension.canal.isin(['Tienda', 'E-commerce']).all():
        raise ValueError('Canal desconocido')
    for registro in sucursales_dimension.itertuples():
        if registro.canal == 'Tienda' and (not registro.comuna or registro.region not in REGIONES or (not -90 <= float(registro.latitud) <= 90) or (not -180 <= float(registro.longitud) <= 180)):
            raise ValueError('Geografia de tienda invalida')
    sucursales_dimension = sucursales_dimension.sort_values('codigo_sucursal').reset_index(drop=True)
    sucursales_dimension.insert(0, 'clave_sucursal_canal', range(1, len(sucursales_dimension) + 1))
    sucursales_dimension[['latitud', 'longitud']] = sucursales_dimension[['latitud', 'longitud']].apply(pd.to_numeric, errors='coerce')
    conciliar('sucursales', len(sucursales_dimension))
    return sucursales_dimension
