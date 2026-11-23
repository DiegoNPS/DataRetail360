"""Controles de integridad y concordancia de la base cargada."""
from sqlalchemy import text

CONTROLES = {
    'versiones_cliente_solapadas': """
        SELECT COUNT(*) FROM dim_cliente a JOIN dim_cliente b
        ON a.id_cliente=b.id_cliente AND a.clave_cliente<b.clave_cliente
        AND a.vigente_desde<b.vigente_hasta AND b.vigente_desde<a.vigente_hasta
    """,
    'versiones_actuales_invalidas': """
        SELECT COUNT(*) FROM (SELECT id_cliente FROM dim_cliente
        GROUP BY id_cliente HAVING SUM(es_actual)<>1)
    """,
    'version_cliente_incorrecta': """
        SELECT COUNT(*) FROM hecho_ventas v JOIN dim_fecha f USING(clave_fecha)
        JOIN dim_cliente c USING(clave_cliente)
        WHERE f.fecha<c.vigente_desde OR f.fecha>=c.vigente_hasta
    """,
    'exceso_devoluciones': """
        SELECT COUNT(*) FROM (SELECT v.clave_venta FROM hecho_ventas v
        JOIN hecho_devoluciones d USING(clave_venta) GROUP BY v.clave_venta
        HAVING SUM(d.cantidad_devuelta)>v.cantidad
        OR SUM(d.importe_devuelto)>v.importe_tras_descuento)
    """,
    'devolucion_anterior_venta': """
        SELECT COUNT(*) FROM hecho_devoluciones d JOIN hecho_ventas v USING(clave_venta)
        WHERE d.clave_fecha<v.clave_fecha
    """,
    'dimensiones_devolucion_incoherentes': """
        SELECT COUNT(*) FROM hecho_devoluciones d JOIN hecho_ventas v USING(clave_venta)
        WHERE d.clave_producto<>v.clave_producto OR d.clave_cliente<>v.clave_cliente
        OR d.clave_sucursal_canal<>v.clave_sucursal_canal
    """,
    'claves_venta_duplicadas': """
        SELECT COUNT(*) FROM (SELECT clave_negocio FROM hecho_ventas
        GROUP BY clave_negocio HAVING COUNT(*)>1)
    """,
    'importe_venta_invalido': """
        SELECT COUNT(*) FROM hecho_ventas WHERE importe_tras_descuento<>
        CAST((importe_bruto*(100-porcentaje_descuento)+50)/100 AS INTEGER)
    """,
    'grano_stock_duplicado': """
        SELECT COUNT(*) FROM (
            SELECT clave_fecha,clave_producto,clave_sucursal_canal
            FROM hecho_stock_diario
            GROUP BY clave_fecha,clave_producto,clave_sucursal_canal
            HAVING COUNT(*)>1
        )
    """,
    'medidas_stock_incoherentes': """
        SELECT COUNT(*) FROM hecho_stock_diario
        WHERE stock_disponible<>stock_fisico-stock_reservado
           OR valor_stock<>stock_fisico*costo_unitario
           OR stock_reservado>stock_fisico
    """,
    'stock_fuera_de_tienda': """
        SELECT COUNT(*) FROM hecho_stock_diario h
        JOIN dim_sucursal_canal s USING(clave_sucursal_canal)
        WHERE s.canal<>'Tienda'
    """,
}


def validar_carga(conexion, tablas, conciliacion):
    """Comprueba integridad, reglas y concordancia entre memoria y SQLite."""
    controles = {nombre: int(conexion.execute(text(sql)).scalar())
                 for nombre, sql in CONTROLES.items()}
    controles['referencias_huerfanas'] = len(conexion.exec_driver_sql('PRAGMA foreign_key_check').fetchall())
    controles['descuadre_conciliacion'] = int(conciliacion['diferencia'].abs().sum())
    for nombre, datos in tablas.items():
        filas = int(conexion.execute(text(f'SELECT COUNT(*) FROM {nombre}')).scalar())
        controles['conteo_' + nombre] = abs(filas - len(datos))
    if any(controles.values()):
        raise ValueError(f'No se publica la base: controles fallidos {controles}')
    return controles
