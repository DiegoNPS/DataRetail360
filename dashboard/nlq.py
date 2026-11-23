"""Consulta en lenguaje natural con SQL seguro y validación explícita."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel, Field

from dashboard.datos import leer_sql


VISTAS_PERMITIDAS = {
    "vista_ventas_netas", "vista_stock_tiendas", "vista_actividad_mensual",
    "vista_ventas_por_producto", "vista_ventas_por_sucursal",
}
PALABRAS_PROHIBIDAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|PRAGMA|ATTACH|DETACH|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


class ConsultaSQL(BaseModel):
    sql: str = Field(description="Una única consulta SQLite SELECT o WITH de solo lectura")
    explicacion: str
    supuestos: list[str] = []


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    nivel: str
    mensajes: tuple[str, ...]


CONSULTAS_CURADAS = {
    "¿Cuál fue la venta neta por año?": """
        SELECT anio, ROUND(SUM(importe_neto),0) AS venta_neta
        FROM vista_ventas_netas GROUP BY anio ORDER BY anio
    """,
    "¿Qué categorías tienen mayor venta neta?": """
        SELECT categoria, ROUND(SUM(importe_neto),0) AS venta_neta
        FROM vista_ventas_netas GROUP BY categoria ORDER BY venta_neta DESC
    """,
    "¿Qué tiendas presentan más quiebres en el último cierre?": """
        SELECT nombre_sucursal,
               SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END) AS quiebres
        FROM vista_stock_tiendas
        WHERE fecha_stock=(SELECT MAX(fecha_stock) FROM vista_stock_tiendas)
        GROUP BY nombre_sucursal ORDER BY quiebres DESC LIMIT 10
    """,
    "¿Cómo evolucionó la tasa de quiebre durante los 30 días?": """
        SELECT fecha_stock,
               ROUND(100.0*SUM(CASE WHEN stock_disponible=0 THEN 1 ELSE 0 END)/COUNT(*),2) tasa_quiebre_pct
        FROM vista_stock_tiendas GROUP BY fecha_stock ORDER BY fecha_stock
    """,
}


def validar_sql(sql: str) -> ResultadoValidacion:
    limpio = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.MULTILINE | re.DOTALL).strip()
    errores = []
    if not re.match(r"^(SELECT|WITH)\b", limpio, re.IGNORECASE):
        errores.append("La consulta debe comenzar con SELECT o WITH.")
    if PALABRAS_PROHIBIDAS.search(limpio):
        errores.append("Contiene una operación no permitida.")
    sin_final = limpio[:-1] if limpio.endswith(";") else limpio
    if ";" in sin_final:
        errores.append("Solo se permite una sentencia SQL.")
    tablas = {t.lower() for t in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*)", limpio, re.IGNORECASE)}
    nombres_cte = {t.lower() for t in re.findall(
        r"(?:\bWITH\b|,)\s*([A-Za-z_][\w]*)\s+AS\s*\(", limpio, re.IGNORECASE
    )}
    tablas -= nombres_cte
    no_permitidas = sorted(tablas - VISTAS_PERMITIDAS)
    if no_permitidas:
        errores.append("Fuentes no permitidas: " + ", ".join(no_permitidas))
    if not tablas:
        errores.append("La consulta no referencia una vista aprobada.")
    return ResultadoValidacion(not errores, "Estructural", tuple(errores or [
        "SQL de solo lectura, una sentencia y fuentes aprobadas.",
        "La interpretación de negocio aún requiere revisión humana.",
    ]))


def ejecutar_sql_seguro(sql: str) -> tuple[pd.DataFrame, ResultadoValidacion]:
    validacion = validar_sql(sql)
    if not validacion.valido:
        return pd.DataFrame(), validacion
    try:
        resultado = leer_sql(f"SELECT * FROM ({sql.rstrip().rstrip(';')}) LIMIT 200")
    except Exception as exc:
        return pd.DataFrame(), ResultadoValidacion(False, "Ejecución", (f"SQLite rechazó la consulta: {exc}",))
    return resultado, validacion


def ejecutar_curada(pregunta: str):
    sql = CONSULTAS_CURADAS[pregunta]
    resultado, validacion = ejecutar_sql_seguro(sql)
    if validacion.valido:
        referencia = leer_sql(sql)
        coincide = resultado.reset_index(drop=True).equals(referencia.head(200).reset_index(drop=True))
        validacion = ResultadoValidacion(
            coincide, "Resultado validado",
            ("Coincide con la consulta de referencia independiente." if coincide
             else "El resultado no coincide con la referencia; requiere revisión.",),
        )
    return sql, resultado, validacion


def generar_sql(pregunta: str) -> ConsultaSQL:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("No se configuró OPENAI_API_KEY; use las preguntas curadas verificables.")
    from openai import OpenAI
    catalogo = """Vistas permitidas:
- vista_ventas_netas(fecha, anio, mes, categoria, canal, region_sucursal, nombre_sucursal,
  importe_tras_descuento, importe_devoluciones, importe_neto, cantidad_neta)
- vista_stock_tiendas(fecha_stock, categoria, region_sucursal, nombre_sucursal, nombre_producto,
  stock_fisico, stock_reservado, stock_disponible, stock_en_transito, valor_stock, estado_stock)
- vista_actividad_mensual(anio, mes, canal, ventas_netas, devoluciones)
- vista_ventas_por_producto(categoria, nombre_producto, ventas_netas, unidades_netas)
- vista_ventas_por_sucursal(region_sucursal, nombre_sucursal, canal, ventas_netas, devoluciones)
Reglas: genera una sola consulta SQLite SELECT/WITH; usa solo esas vistas; no inventes columnas;
el stock es snapshot y no se suma entre fechas; para stock actual filtra MAX(fecha_stock)."""
    respuesta = OpenAI().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        input=[
            {"role": "system", "content": "Eres analista SQL. " + catalogo},
            {"role": "user", "content": pregunta},
        ],
        text_format=ConsultaSQL,
    )
    if respuesta.output_parsed is None:
        raise RuntimeError("El modelo no entregó una consulta estructurada.")
    return respuesta.output_parsed
