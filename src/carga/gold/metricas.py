"""Métricas y huellas calculadas desde los datos efectivamente cargados en Gold."""
import hashlib
import pandas as pd
from sqlalchemy import text


def consultar_resultados(conexion, tablas):
    """Calcula métricas y huellas desde las tablas efectivamente cargadas."""
    metricas = dict(conexion.execute(text('''
        SELECT SUM(importe_bruto) ventas_brutas,
               SUM(importe_descuento) descuentos,
               SUM(importe_tras_descuento) ventas_tras_descuento
        FROM hecho_ventas
    ''')).mappings().one())
    metricas['devoluciones'] = int(conexion.execute(text('SELECT COALESCE(SUM(importe_devuelto),0) FROM hecho_devoluciones')).scalar())
    metricas['ventas_netas'] = metricas['ventas_tras_descuento'] - metricas['devoluciones']
    metricas['comprobantes'] = int(conexion.execute(text('''
        SELECT COUNT(*) FROM (SELECT sistema_origen,id_comprobante
        FROM hecho_ventas GROUP BY sistema_origen,id_comprobante)
    ''')).scalar())
    metricas['ticket_promedio_antes_devoluciones'] = metricas['ventas_tras_descuento'] / metricas['comprobantes']
    huellas = {}
    for nombre in tablas:
        datos = pd.read_sql_query(text(f'SELECT * FROM {nombre} ORDER BY 1'), conexion)
        datos = datos.drop(columns=['id_ejecucion'], errors='ignore')
        huellas[nombre] = hashlib.sha256(datos.to_csv(index=False).encode('utf-8')).hexdigest()
    return metricas, huellas
