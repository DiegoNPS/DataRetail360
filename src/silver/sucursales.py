"""Normalización y validación de sucursales y canales."""
import pandas as pd

from ..comun.dominios import REGIONES


def limpiar_sucursales(contexto):
    """Depura el maestro de sucursales y comprueba su geografía."""
    sucursales = contexto.fuentes["sucursales"].copy()
    sucursales["codigo_sucursal"] = sucursales["codigo_sucursal"].str.strip().str.upper()
    if sucursales[["codigo_sucursal", "nombre_sucursal", "canal", "pais"]].eq("").any().any():
        raise ValueError("sucursales: campo obligatorio vacio")
    if sucursales["codigo_sucursal"].duplicated().any():
        raise ValueError("Clave maestra duplicada")
    if not sucursales["canal"].isin(["Tienda", "E-commerce"]).all():
        raise ValueError("Canal desconocido")
    for fila in sucursales.itertuples():
        if fila.canal == "Tienda" and (
            not fila.comuna
            or fila.region not in REGIONES
            or not -90 <= float(fila.latitud) <= 90
            or not -180 <= float(fila.longitud) <= 180
        ):
            raise ValueError("Geografia de tienda invalida")
    sucursales[["latitud", "longitud"]] = sucursales[["latitud", "longitud"]].apply(
        pd.to_numeric, errors="coerce"
    )
    sucursales = sucursales.sort_values("codigo_sucursal").reset_index(drop=True)
    sucursales["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("sucursales", len(sucursales))
    return sucursales
