"""Casos de formato y efecto real en limpieza/conciliación de clientes."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.comun.correos import correo_valido
from src.silver.clientes import limpiar_clientes


class PruebasCorreos(unittest.TestCase):
    def test_formatos_y_dominios_variados(self):
        for correo in ['ana@gmail.com', 'ana.perez@hotmail.com', 'ana_12@outlook.com',
                       'ana+compras@example.com', 'ventas@tienda.example.org',
                       "o'hara@dominio-cl.example.com"]:
            with self.subTest(correo=correo):
                self.assertTrue(correo_valido(correo))

    def test_malformados_y_limites(self):
        for correo in ['', None, 'sin-arroba', 'a@@gmail.com', '.a@gmail.com',
                       'a.@gmail.com', 'a..b@gmail.com', 'a b@gmail.com',
                       'a@-dominio.com', 'a@dominio-.com', 'a@dominio..com',
                       'a@dominio', 'a@dominio.c', 'a@dominio.123',
                       'a@dominio_com.cl', 'a' * 65 + '@example.com',
                       'a@' + 'b' * 64 + '.com', 'ñ@example.com']:
            with self.subTest(correo=correo):
                self.assertFalse(correo_valido(correo))

    def test_silver_normaliza_rechaza_y_concilia(self):
        filas = [
            ['C1', ' Ana+Compras@GMAIL.COM ', 'Metropolitana', 'Ocasional', '2024-01-01'],
            ['C1', 'ana+compras@gmail.com', 'Metropolitana', 'Ocasional', '2024-01-01'],
            ['C2', 'dos@@hotmail.com', 'Metropolitana', 'Ocasional', '2024-01-01'],
            ['C3', '', 'Metropolitana', 'Ocasional', '2024-01-01'],
        ]
        contexto = SimpleNamespace(
            fuentes={'clientes': pd.DataFrame(filas, columns=['id_cliente','correo','region','segmento','vigente_desde']),
                     'cambios_cliente': pd.DataFrame(columns=['id_cliente','fecha_efectiva','nueva_region','nuevo_segmento'])},
            id_ejecucion='PRUEBA', duplicados=[], rechazos=[], conciliaciones=[])
        contexto.rechazar = lambda fuente, indice, fila, motivo: contexto.rechazos.append((fuente, indice, motivo))
        contexto.conciliar = lambda *args: contexto.conciliaciones.append(args)
        clientes, _ = limpiar_clientes(contexto)
        self.assertEqual(clientes['correo'].tolist(), ['ana+compras@gmail.com'])
        self.assertEqual([r[2] for r in contexto.rechazos], ['correo_formato_invalido','correo_vacio'])
        self.assertEqual(len(contexto.duplicados), 1)
        self.assertIn(('clientes', 1, 1), contexto.conciliaciones)


if __name__ == '__main__':
    unittest.main()
