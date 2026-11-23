"""Genera la fuente sintética reproducible de stock inicial de tiendas."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


def generar(carpeta_entrada):
    """Crea un snapshot al cierre del período para producto-tienda."""
    carpeta = Path(carpeta_entrada)
    productos = pd.read_csv(carpeta / "productos.csv", dtype=str)
    sucursales = pd.read_csv(carpeta / "sucursales.csv", dtype=str)
    ventas = pd.read_csv(carpeta / "ventas.csv", usecols=["fecha_venta"], dtype=str)
    tiendas = sucursales[sucursales["canal"].eq("Tienda")].reset_index(drop=True)
    fecha = ventas["fecha_venta"].max()
    filas = []
    for indice_producto, producto in productos.reset_index(drop=True).iterrows():
        for indice_tienda, tienda in tiendas.iterrows():
            semilla = (indice_producto + 1) * 37 + (indice_tienda + 1) * 53
            stock_fisico = 0 if semilla % 20 == 0 else 5 + semilla % 96
            stock_reservado = 0 if stock_fisico == 0 else semilla % min(8, stock_fisico + 1)
            stock_en_transito = semilla % (31 if stock_fisico < 20 else 11)
            filas.append(
                {
                    "fecha_stock": fecha,
                    "codigo_producto": producto["codigo_producto"],
                    "codigo_sucursal": tienda["codigo_sucursal"],
                    "stock_fisico": stock_fisico,
                    "stock_reservado": stock_reservado,
                    "stock_en_transito": stock_en_transito,
                    "costo_unitario": int(producto["costo_unitario"]),
                }
            )
    salida = carpeta / "stock_diario.csv"
    pd.DataFrame(filas).to_csv(salida, index=False, encoding="utf-8")
    huella = hashlib.sha256(salida.read_bytes()).hexdigest()
    print({"archivo": salida.name, "filas": len(filas), "sha256": huella})


if __name__ == "__main__":
    generar(Path(__file__).resolve().parents[2] / "datos" / "entrada")
