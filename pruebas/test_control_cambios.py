from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import pandas as pd

from src.extraccion.lector_csv import leer_csv_validado
from src.gold.control_cambios import controlar_cambios_clientes


RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "datos" / "entrada"


class PruebasControlCambios(unittest.TestCase):
    def test_bronze_modificado_se_carga_y_queda_auditado(self):
        manifiesto = json.loads((ENTRADA / "manifiesto.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            clientes = pd.read_csv(
                ENTRADA / "clientes.csv", dtype=str, keep_default_na=False,
                encoding="utf-8-sig",
            )
            clientes.loc[0, "correo"] = "correo.cambiado@example.com"
            clientes.to_csv(carpeta / "clientes.csv", index=False, encoding="utf-8-sig")

            frame, registro = leer_csv_validado(
                carpeta,
                "clientes",
                "id_cliente correo region segmento vigente_desde",
                manifiesto,
                "ETL-PRUEBA",
            )

        self.assertEqual(len(frame), len(clientes))
        self.assertEqual(registro["estado_fuente"], "MODIFICADA")
        self.assertIn("contenido", registro["detalle_cambio"])
        self.assertNotEqual(registro["sha256"], registro["sha256_esperado"])

    def test_correo_cambiado_es_scd1_y_preserva_historial(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal) / "anterior.sqlite"
            with closing(sqlite3.connect(base)) as conexion:
                conexion.execute(
                    """CREATE TABLE dim_cliente(
                           id_cliente TEXT, correo_normalizado TEXT, es_actual INTEGER)"""
                )
                conexion.execute(
                    "INSERT INTO dim_cliente VALUES('CLI-1','anterior@example.com',1)"
                )
                conexion.execute(
                    """CREATE TABLE etl_cambios_cliente(
                           id_ejecucion TEXT,id_cliente TEXT,campo TEXT,tipo_scd INTEGER,
                           tipo_evento TEXT,valor_anterior TEXT,valor_nuevo TEXT,
                           detectado_en TEXT)"""
                )
                conexion.execute(
                    """INSERT INTO etl_cambios_cliente VALUES(
                           'ETL-ANT','CLI-0','correo_normalizado',1,'MODIFICACION',
                           'a@example.com','b@example.com','2026-01-01')"""
                )
                conexion.commit()

            actual = pd.DataFrame(
                [{"id_cliente": "CLI-1", "correo_normalizado": "nuevo@example.com",
                  "es_actual": 1}]
            )
            completo, cambios = controlar_cambios_clientes(
                base, actual, "ETL-NUEVA", "2026-11-23"
            )

        self.assertEqual(len(completo), 2)
        self.assertEqual(len(cambios), 1)
        cambio = cambios.iloc[0]
        self.assertEqual(cambio["tipo_evento"], "MODIFICACION")
        self.assertEqual(cambio["tipo_scd"], 1)
        self.assertEqual(cambio["valor_anterior"], "anterior@example.com")
        self.assertEqual(cambio["valor_nuevo"], "nuevo@example.com")


if __name__ == "__main__":
    unittest.main()
