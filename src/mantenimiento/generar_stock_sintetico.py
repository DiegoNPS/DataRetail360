"""Genera un historial sintético reproducible de stock diario por tienda."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


DIAS_HISTORICO_PREDETERMINADOS = 30


def _actualizar_manifiesto(
    carpeta, salida, filas, fecha_inicio, fecha_fin, cantidad_productos, cantidad_tiendas
):
    """Actualiza explícitamente la línea base de la fuente regenerada."""
    ruta = carpeta / "manifiesto.json"
    manifiesto = json.loads(ruta.read_text(encoding="utf-8"))
    entrada = next(
        item for item in manifiesto["archivos"] if item["archivo"] == salida.name
    )
    entrada["filas"] = filas
    entrada["sha256"] = hashlib.sha256(salida.read_bytes()).hexdigest()
    manifiesto["version_datos"] = "360-stock-v2"
    filas_formateadas = f"{filas:,}".replace(",", ".")
    productos_formateados = f"{cantidad_productos:,}".replace(",", ".")
    manifiesto["nota_stock"] = (
        f"Snapshots diarios sintéticos desde {fecha_inicio} hasta {fecha_fin} para "
        f"{productos_formateados} productos en {cantidad_tiendas} tiendas físicas; "
        f"{filas_formateadas} filas."
    )
    ruta.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return entrada["sha256"]


def generar(carpeta_entrada, dias=DIAS_HISTORICO_PREDETERMINADOS):
    """Crea snapshots al cierre diario con grano fecha-producto-tienda."""
    if dias < 1:
        raise ValueError("dias debe ser un entero positivo")
    carpeta = Path(carpeta_entrada)
    productos = pd.read_csv(carpeta / "productos.csv", dtype=str)
    sucursales = pd.read_csv(carpeta / "sucursales.csv", dtype=str)
    ventas = pd.read_csv(carpeta / "ventas.csv", usecols=["fecha_venta"], dtype=str)
    tiendas = sucursales[sucursales["canal"].eq("Tienda")].reset_index(drop=True)
    productos = productos.reset_index(drop=True)
    fecha_fin = pd.Timestamp(ventas["fecha_venta"].max())
    fechas = pd.date_range(end=fecha_fin, periods=dias, freq="D")
    filas = []
    for indice_dia, fecha in enumerate(fechas):
        for indice_producto, producto in productos.iterrows():
            for indice_tienda, tienda in tiendas.iterrows():
                semilla = (indice_producto + 1) * 37 + (indice_tienda + 1) * 53
                ciclo_reposicion = 5 + semilla % 6
                posicion_ciclo = (indice_dia + semilla) % ciclo_reposicion
                consumo_diario = 1 + semilla % 5
                nivel_reposicion = 20 + semilla % 81
                stock_fisico = max(
                    0, nivel_reposicion - posicion_ciclo * consumo_diario
                )
                stock_reservado = min(stock_fisico, (semilla + indice_dia) % 8)
                dias_para_reposicion = ciclo_reposicion - posicion_ciclo - 1
                stock_en_transito = (
                    10 + semilla % 41 if dias_para_reposicion <= 2 else 0
                )
                filas.append(
                    {
                        "fecha_stock": fecha.strftime("%Y-%m-%d"),
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
    huella = _actualizar_manifiesto(
        carpeta,
        salida,
        len(filas),
        fechas.min().strftime("%Y-%m-%d"),
        fechas.max().strftime("%Y-%m-%d"),
        len(productos),
        len(tiendas),
    )
    print(
        {
            "archivo": salida.name,
            "filas": len(filas),
            "dias": dias,
            "fecha_inicio": fechas.min().strftime("%Y-%m-%d"),
            "fecha_fin": fechas.max().strftime("%Y-%m-%d"),
            "sha256": huella,
        }
    )


if __name__ == "__main__":
    analizador = argparse.ArgumentParser()
    analizador.add_argument(
        "--dias", type=int, default=DIAS_HISTORICO_PREDETERMINADOS
    )
    argumentos = analizador.parse_args()
    generar(
        Path(__file__).resolve().parents[2] / "datos" / "entrada",
        dias=argumentos.dias,
    )
