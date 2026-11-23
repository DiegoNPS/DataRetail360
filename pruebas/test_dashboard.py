"""Pruebas del dashboard, sus KPI y la consulta segura."""
import unittest

from dashboard.datos import fecha_stock_mas_reciente, resumen_stock, resumen_ventas
from dashboard.kpis import catalogo_como_filas
from dashboard.nlq import CONSULTAS_CURADAS, ejecutar_curada, validar_sql


class PruebasDashboard(unittest.TestCase):
    def test_catalogo_kpi_completo(self):
        filas = catalogo_como_filas()
        self.assertEqual(len(filas), 5)
        obligatorios = {"nombre", "formula", "fuente", "meta", "alerta", "dueno", "utilidad"}
        for fila in filas:
            self.assertTrue(obligatorios.issubset(fila))
            self.assertTrue(all(fila[campo] for campo in obligatorios))

    def test_venta_neta_concilia_con_gold(self):
        resumen = resumen_ventas("2024-01-01", "2025-12-31")
        self.assertEqual(resumen["venta_neta"], 86_307_738_295)

    def test_stock_actual_usa_un_solo_snapshot(self):
        self.assertEqual(fecha_stock_mas_reciente(), "2025-12-31")
        resumen = resumen_stock()
        self.assertEqual(resumen["posiciones"], 20_000)
        self.assertEqual(resumen["stock_disponible"], 976_552)
        self.assertAlmostEqual(resumen["tasa_quiebre"], 2.145, places=3)

    def test_sql_destructivo_y_fuente_desconocida_se_rechazan(self):
        for sql in (
            "DROP TABLE hecho_ventas",
            "SELECT * FROM hecho_ventas",
            "SELECT * FROM vista_ventas_netas; DELETE FROM hecho_ventas",
            "PRAGMA table_info(vista_ventas_netas)",
        ):
            self.assertFalse(validar_sql(sql).valido, sql)

    def test_select_de_vista_aprobada_se_acepta(self):
        self.assertTrue(validar_sql("SELECT anio FROM vista_ventas_netas LIMIT 1").valido)
        self.assertTrue(validar_sql(
            "WITH ventas AS (SELECT anio FROM vista_ventas_netas) SELECT * FROM ventas"
        ).valido)

    def test_consultas_curadas_coinciden_con_referencia(self):
        for pregunta in CONSULTAS_CURADAS:
            _, resultado, validacion = ejecutar_curada(pregunta)
            self.assertTrue(validacion.valido, pregunta)
            self.assertFalse(resultado.empty, pregunta)


if __name__ == "__main__":
    unittest.main()
