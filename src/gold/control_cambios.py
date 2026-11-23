"""Control de cambios de clientes entre la carga actual y Gold publicado."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd


COLUMNAS_CAMBIOS = [
    "id_ejecucion",
    "id_cliente",
    "campo",
    "tipo_scd",
    "tipo_evento",
    "valor_anterior",
    "valor_nuevo",
    "detectado_en",
]


def _tabla_existe(conexion, nombre):
    return conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nombre,)
    ).fetchone() is not None


def _vacio():
    return pd.DataFrame(columns=COLUMNAS_CAMBIOS)


def controlar_cambios_clientes(ruta_base, dimension_actual, id_ejecucion, detectado_en):
    """Compara clientes con la última base y conserva el historial de auditoría.

    El correo es un atributo SCD 1: una corrección sustituye el valor en todas las
    versiones reconstruidas, pero el valor anterior y el nuevo quedan trazados.
    Altas y bajas también se registran como eventos, sin asignarles un tipo SCD.
    La primera carga establece la línea base y no genera miles de falsas altas.
    """
    ruta_base = Path(ruta_base)
    if not ruta_base.exists():
        return _vacio(), _vacio()

    with closing(sqlite3.connect(ruta_base)) as conexion:
        if not _tabla_existe(conexion, "dim_cliente"):
            return _vacio(), _vacio()
        anterior = pd.read_sql_query(
            """SELECT id_cliente, correo_normalizado
               FROM dim_cliente WHERE es_actual=1""",
            conexion,
        )
        historial = (
            pd.read_sql_query(
                """SELECT id_ejecucion,id_cliente,campo,tipo_scd,tipo_evento,
                          valor_anterior,valor_nuevo,detectado_en
                   FROM etl_cambios_cliente ORDER BY rowid""",
                conexion,
            )
            if _tabla_existe(conexion, "etl_cambios_cliente")
            else _vacio()
        )

    actual = dimension_actual.loc[
        dimension_actual["es_actual"].eq(1), ["id_cliente", "correo_normalizado"]
    ].copy()
    comparacion = actual.merge(
        anterior,
        on="id_cliente",
        how="outer",
        suffixes=("_nuevo", "_anterior"),
        indicator=True,
    )
    eventos = []
    for _, fila in comparacion.iterrows():
        if fila["_merge"] == "left_only":
            eventos.append(
                [id_ejecucion, fila["id_cliente"], "cliente", None, "ALTA", None,
                 fila["correo_normalizado_nuevo"], detectado_en]
            )
        elif fila["_merge"] == "right_only":
            eventos.append(
                [id_ejecucion, fila["id_cliente"], "cliente", None, "BAJA",
                 fila["correo_normalizado_anterior"], None, detectado_en]
            )
        elif fila["correo_normalizado_nuevo"] != fila["correo_normalizado_anterior"]:
            eventos.append(
                [id_ejecucion, fila["id_cliente"], "correo_normalizado", 1,
                 "MODIFICACION", fila["correo_normalizado_anterior"],
                 fila["correo_normalizado_nuevo"], detectado_en]
            )
    actuales = pd.DataFrame(eventos, columns=COLUMNAS_CAMBIOS)
    completo = pd.concat([historial, actuales], ignore_index=True)
    return completo, actuales
