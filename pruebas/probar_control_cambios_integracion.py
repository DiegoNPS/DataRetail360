"""Prueba pesada opcional: una edición Bronze válida se avisa y se audita."""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.proceso import ejecutar_completo


with tempfile.TemporaryDirectory() as temporal:
    raiz_prueba = Path(temporal) / "proyecto"
    entrada = raiz_prueba / "datos" / "entrada"
    shutil.copytree(RAIZ / "datos" / "entrada", entrada)

    ejecutar_completo(raiz_prueba, entrada, informar=lambda mensaje: None)

    ruta_clientes = entrada / "clientes.csv"
    clientes = pd.read_csv(
        ruta_clientes, dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    conteos_id = clientes["id_cliente"].str.strip().str.upper().value_counts()
    indice = clientes.index[
        clientes["id_cliente"].str.strip().str.upper().map(conteos_id).eq(1)
    ][0]
    id_cliente = clientes.loc[indice, "id_cliente"]
    correo_anterior = clientes.loc[indice, "correo"].strip().lower()
    correo_nuevo = "correo.cambiado@example.com"
    clientes.loc[indice, "correo"] = correo_nuevo
    clientes.to_csv(ruta_clientes, index=False, encoding="utf-8-sig")

    mensajes = []
    resumen = ejecutar_completo(raiz_prueba, entrada, informar=mensajes.append)
    base = raiz_prueba / "resultados" / "dataretail360.sqlite"
    with closing(sqlite3.connect(base)) as conexion:
        cambio = conexion.execute(
            """SELECT tipo_scd,tipo_evento,valor_anterior,valor_nuevo
               FROM etl_cambios_cliente
               WHERE id_cliente=? AND campo='correo_normalizado'
               ORDER BY id_cambio DESC LIMIT 1""",
            (id_cliente,),
        ).fetchone()
        fuente = conexion.execute(
            """SELECT estado_fuente,sha256=sha256_esperado
               FROM etl_fuentes WHERE archivo='clientes.csv'"""
        ).fetchone()

    assert resumen["fuentes_modificadas"]
    assert resumen["cambios_cliente_detectados"] == 1
    assert any("AVISO: Bronze cambió" in mensaje for mensaje in mensajes)
    assert any("AVISO: se detectaron 1 cambios" in mensaje for mensaje in mensajes)
    assert fuente == ("MODIFICADA", 0)
    assert cambio == (1, "MODIFICACION", correo_anterior, correo_nuevo)

print("CONTROL_CAMBIOS_INTEGRACION_OK")
