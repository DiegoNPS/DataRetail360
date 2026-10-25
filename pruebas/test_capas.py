from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "datos" / "entrada"
SILVER = RAIZ / "resultados" / "silver"
BASE = RAIZ / "resultados" / "dataretail360.sqlite"
CLAVES_GOLD = {
    "clave_fecha",
    "clave_producto",
    "clave_cliente",
    "clave_sucursal_canal",
    "clave_venta",
    "clave_devolucion",
}


class PruebasCapas(unittest.TestCase):
    def test_bronze_conserva_huellas_y_filas(self):
        manifiesto = json.loads((ENTRADA / "manifiesto.json").read_text(encoding="utf-8"))
        for entrada in manifiesto["archivos"]:
            ruta = ENTRADA / entrada["archivo"]
            self.assertEqual(hashlib.sha256(ruta.read_bytes()).hexdigest(), entrada["sha256"])
            self.assertEqual(len(pd.read_csv(ruta, dtype=str, keep_default_na=False)), entrada["filas"])

    def test_silver_tiene_siete_entidades_sin_claves_sustitutas(self):
        manifiesto = json.loads((SILVER / "manifiesto_silver.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["version_contrato"], 2)
        self.assertEqual(len(manifiesto["entidades"]), 7)
        for entrada in manifiesto["entidades"]:
            datos = pd.read_parquet(SILVER / entrada["archivo"])
            self.assertFalse(CLAVES_GOLD.intersection(datos.columns), entrada["entidad"])
            self.assertEqual(len(datos), entrada["filas"])
        auditoria = json.loads((SILVER / "auditoria_silver.json").read_text(encoding="utf-8"))
        self.assertTrue(all(fila["diferencia"] == 0 for fila in auditoria["conciliacion"]))

    def test_gold_conserva_conteos_y_metricas_de_negocio(self):
        with closing(sqlite3.connect(BASE)) as conexion:
            conteos = conexion.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM dim_fecha),
                    (SELECT COUNT(*) FROM dim_producto),
                    (SELECT COUNT(*) FROM dim_cliente),
                    (SELECT COUNT(*) FROM dim_sucursal_canal),
                    (SELECT COUNT(*) FROM hecho_ventas),
                    (SELECT COUNT(*) FROM hecho_devoluciones)
                """
            ).fetchone()
            self.assertEqual(conteos, (731, 1000, 12000, 22, 125217, 4612))
            metricas = conexion.execute(
                """
                SELECT
                    SUM(importe_bruto),
                    SUM(importe_descuento),
                    SUM(importe_tras_descuento),
                    SUM(importe_tras_descuento)
                      - (SELECT COALESCE(SUM(importe_devuelto), 0) FROM hecho_devoluciones)
                FROM hecho_ventas
                """
            ).fetchone()
            self.assertEqual(
                metricas,
                (94699501000, 6758099015, 87941401985, 86307738295),
            )

    def test_gold_tiene_seis_vistas_y_sin_huerfanos(self):
        with closing(sqlite3.connect(BASE)) as conexion:
            vistas = {
                fila[0]
                for fila in conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type='view'"
                ).fetchall()
            }
            self.assertEqual(
                vistas,
                {
                    "vista_detalle_ventas",
                    "vista_detalle_devoluciones",
                    "vista_ventas_netas",
                    "vista_actividad_mensual",
                    "vista_ventas_por_producto",
                    "vista_ventas_por_sucursal",
                },
            )
            self.assertEqual(conexion.execute("PRAGMA foreign_key_check").fetchall(), [])
            suma_vista = conexion.execute(
                "SELECT SUM(importe_tras_descuento), SUM(importe_devoluciones) FROM vista_ventas_netas"
            ).fetchone()
            self.assertEqual(suma_vista, (87941401985, 1633663690))


if __name__ == "__main__":
    unittest.main()

