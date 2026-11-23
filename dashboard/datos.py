"""Consultas de solo lectura al modelo dimensional Gold."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
RUTA_DB = RAIZ / "resultados" / "dataretail360.sqlite"


def conectar_solo_lectura(ruta: Path = RUTA_DB) -> sqlite3.Connection:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la base Gold: {ruta}. Ejecute primero el ETL.")
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=10)
    conexion.execute("PRAGMA query_only=ON")
    return conexion


def leer_sql(sql: str, parametros=(), ruta: Path = RUTA_DB) -> pd.DataFrame:
    with conectar_solo_lectura(ruta) as conexion:
        return pd.read_sql_query(sql, conexion, params=parametros)


def limites_y_filtros() -> dict:
    fechas = leer_sql("SELECT MIN(fecha), MAX(fecha) FROM vista_ventas_netas").iloc[0]
    def valores(columna: str) -> list[str]:
        permitidas = {"region_sucursal", "canal", "categoria"}
        if columna not in permitidas:
            raise ValueError("Filtro no permitido")
        return leer_sql(f"SELECT DISTINCT {columna} valor FROM vista_ventas_netas ORDER BY 1")["valor"].tolist()
    return {
        "fecha_min": pd.to_datetime(fechas.iloc[0]).date(),
        "fecha_max": pd.to_datetime(fechas.iloc[1]).date(),
        "regiones": valores("region_sucursal"),
        "canales": valores("canal"),
        "categorias": valores("categoria"),
    }


def _where_ventas(fecha_inicio, fecha_fin, regiones, canales, categorias):
    condiciones = ["fecha BETWEEN ? AND ?"]
    parametros: list[object] = [str(fecha_inicio), str(fecha_fin)]
    for columna, seleccion in (("region_sucursal", regiones), ("canal", canales), ("categoria", categorias)):
        if seleccion:
            condiciones.append(f"{columna} IN ({','.join('?' for _ in seleccion)})")
            parametros.extend(seleccion)
    return " AND ".join(condiciones), parametros


def resumen_ventas(fecha_inicio, fecha_fin, regiones=(), canales=(), categorias=()) -> dict:
    where, params = _where_ventas(fecha_inicio, fecha_fin, regiones, canales, categorias)
    actual = leer_sql(
        f"""SELECT COALESCE(SUM(importe_neto),0) venta_neta,
                   COALESCE(SUM(importe_tras_descuento),0) venta_antes_devoluciones,
                   COALESCE(SUM(importe_devoluciones),0) devoluciones
            FROM vista_ventas_netas WHERE {where}""", params).iloc[0]
    inicio_anterior = pd.Timestamp(fecha_inicio) - pd.DateOffset(years=1)
    fin_anterior = pd.Timestamp(fecha_fin) - pd.DateOffset(years=1)
    where_ant, params_ant = _where_ventas(inicio_anterior.date(), fin_anterior.date(), regiones, canales, categorias)
    anterior = float(leer_sql(
        f"SELECT COALESCE(SUM(importe_neto),0) venta FROM vista_ventas_netas WHERE {where_ant}",
        params_ant).iloc[0, 0])
    venta = float(actual["venta_neta"])
    base = float(actual["venta_antes_devoluciones"])
    return {
        "venta_neta": venta,
        "venta_anterior": anterior,
        "crecimiento": ((venta - anterior) / anterior * 100) if anterior else None,
        "tasa_devoluciones": (float(actual["devoluciones"]) / base * 100) if base else 0.0,
    }


def serie_mensual(fecha_inicio, fecha_fin, regiones=(), canales=(), categorias=()) -> pd.DataFrame:
    where, params = _where_ventas(fecha_inicio, fecha_fin, regiones, canales, categorias)
    return leer_sql(
        f"""SELECT substr(fecha,1,7) mes, SUM(importe_neto) venta_neta
            FROM vista_ventas_netas WHERE {where} GROUP BY 1 ORDER BY 1""", params)


def ventas_por_categoria(fecha_inicio, fecha_fin, regiones=(), canales=(), categorias=()) -> pd.DataFrame:
    where, params = _where_ventas(fecha_inicio, fecha_fin, regiones, canales, categorias)
    return leer_sql(
        f"""SELECT categoria, SUM(importe_neto) venta_neta
            FROM vista_ventas_netas WHERE {where} GROUP BY 1 ORDER BY 2 DESC""", params)


def fecha_stock_mas_reciente() -> str:
    return str(leer_sql("SELECT MAX(fecha_stock) FROM vista_stock_tiendas").iloc[0, 0])


def resumen_stock(fecha_stock: str | None = None, regiones=(), categorias=()) -> dict:
    fecha_stock = fecha_stock or fecha_stock_mas_reciente()
    condiciones = ["fecha_stock = ?"]
    params: list[object] = [fecha_stock]
    for columna, seleccion in (("region_sucursal", regiones), ("categoria", categorias)):
        if seleccion:
            condiciones.append(f"{columna} IN ({','.join('?' for _ in seleccion)})")
            params.extend(seleccion)
    fila = leer_sql(
        f"""SELECT SUM(stock_fisico) stock_fisico, SUM(stock_disponible) stock_disponible,
                   SUM(valor_stock) valor_stock, COUNT(*) posiciones,
                   SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END) quiebres
            FROM vista_stock_tiendas WHERE {' AND '.join(condiciones)}""", params).iloc[0]
    fisico, posiciones = float(fila["stock_fisico"] or 0), int(fila["posiciones"] or 0)
    return {
        "fecha": fecha_stock, "stock_disponible": int(fila["stock_disponible"] or 0),
        "valor_stock": float(fila["valor_stock"] or 0),
        "tasa_quiebre": (int(fila["quiebres"] or 0) / posiciones * 100) if posiciones else 0,
        "disponibilidad": (float(fila["stock_disponible"] or 0) / fisico * 100) if fisico else 0,
        "posiciones": posiciones,
    }


def tendencia_quiebres(regiones=(), categorias=()) -> pd.DataFrame:
    condiciones, params = [], []
    for columna, seleccion in (("region_sucursal", regiones), ("categoria", categorias)):
        if seleccion:
            condiciones.append(f"{columna} IN ({','.join('?' for _ in seleccion)})")
            params.extend(seleccion)
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return leer_sql(
        f"""SELECT fecha_stock,
                   100.0*SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END)/COUNT(*) tasa_quiebre
            FROM vista_stock_tiendas {where} GROUP BY 1 ORDER BY 1""", params)


def quiebres_por_sucursal(fecha_stock=None, regiones=(), categorias=()) -> pd.DataFrame:
    fecha_stock = fecha_stock or fecha_stock_mas_reciente()
    condiciones = ["fecha_stock=?"]
    params: list[object] = [fecha_stock]
    for columna, seleccion in (("region_sucursal", regiones), ("categoria", categorias)):
        if seleccion:
            condiciones.append(f"{columna} IN ({','.join('?' for _ in seleccion)})")
            params.extend(seleccion)
    return leer_sql(
        f"""SELECT region_sucursal, nombre_sucursal,
                   SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END) quiebres,
                   100.0*SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END)/COUNT(*) tasa_quiebre
            FROM vista_stock_tiendas WHERE {' AND '.join(condiciones)}
            GROUP BY 1,2 ORDER BY quiebres DESC, nombre_sucursal LIMIT 15""", params)


def detalle_stock_critico(fecha_stock=None, regiones=(), categorias=(), sucursal=None) -> pd.DataFrame:
    fecha_stock = fecha_stock or fecha_stock_mas_reciente()
    condiciones = ["fecha_stock=?", "stock_disponible<=5"]
    params: list[object] = [fecha_stock]
    for columna, seleccion in (("region_sucursal", regiones), ("categoria", categorias)):
        if seleccion:
            condiciones.append(f"{columna} IN ({','.join('?' for _ in seleccion)})")
            params.extend(seleccion)
    if sucursal:
        condiciones.append("nombre_sucursal=?")
        params.append(sucursal)
    return leer_sql(
        f"""SELECT region_sucursal region, nombre_sucursal sucursal, codigo_producto,
                   nombre_producto producto, categoria, stock_fisico, stock_reservado,
                   stock_disponible, stock_en_transito, estado_stock
            FROM vista_stock_tiendas WHERE {' AND '.join(condiciones)}
            ORDER BY stock_disponible, sucursal, producto LIMIT 500""", params)
