"""Normalización y validación de clientes y sus cambios históricos."""
from __future__ import annotations

import pandas as pd

from ..comun.contratos import CONTRATOS
from ..comun.dominios import REGIONES
from ..comun.utilidades import fecha_valida
from ..comun.correos import correo_valido


SEGMENTOS = ["Ocasional", "Frecuente", "Preferente"]


def intervalos_clientes(
    clientes: pd.DataFrame, cambios: pd.DataFrame
) -> dict[str, list[tuple[str, str]]]:
    """Calcula vigencias naturales para validar ventas sin construir Gold."""
    grupos = {clave: grupo for clave, grupo in cambios.groupby("id_cliente")}
    intervalos: dict[str, list[tuple[str, str]]] = {}
    for cliente in clientes.itertuples():
        desde = cliente.vigente_desde
        limites: list[tuple[str, str]] = []
        for cambio in grupos.get(cliente.id_cliente, pd.DataFrame()).itertuples():
            limites.append((desde, cambio.fecha_efectiva))
            desde = cambio.fecha_efectiva
        limites.append((desde, "9999-12-31"))
        intervalos[cliente.id_cliente] = limites
    return intervalos


def limpiar_clientes(contexto):
    """Depura el maestro de clientes y valida sus eventos SCD tipo 2."""
    clientes = contexto.fuentes["clientes"].copy()
    clientes["id_cliente"] = clientes["id_cliente"].str.strip().str.upper()
    clientes["correo"] = clientes["correo"].str.strip().str.lower()
    obligatorios = [c for c in CONTRATOS["clientes"].split() if c != "correo"]
    if clientes[obligatorios].eq("").any().any():
        raise ValueError("clientes: campo obligatorio vacio")
    duplicadas = clientes.duplicated(keep="first")
    for indice in clientes[duplicadas].index:
        contexto.duplicados.append(
            dict(
                fuente="clientes",
                fila_origen=int(indice) + 2,
                motivo="duplicado_identico_normalizado",
                id_ejecucion=contexto.id_ejecucion,
            )
        )
    clientes = clientes[~duplicadas].copy()
    # Una identidad contradictoria sigue siendo fatal, incluso con correo inválido.
    if clientes["id_cliente"].duplicated().any():
        raise ValueError("Identidad cliente ambigua")
    invalidos = ~clientes["correo"].map(correo_valido)
    for indice, fila in clientes[invalidos].iterrows():
        motivo = "correo_vacio" if not fila["correo"] else "correo_formato_invalido"
        contexto.rechazar("clientes", indice, fila, motivo)
    clientes = clientes[~invalidos].copy()
    if clientes["id_cliente"].duplicated().any() or clientes["correo"].duplicated().any():
        raise ValueError("Identidad cliente ambigua")
    if (
        not clientes["vigente_desde"].map(fecha_valida).all()
        or not clientes["region"].isin(REGIONES).all()
        or not clientes["segmento"].isin(SEGMENTOS).all()
    ):
        raise ValueError("Cliente invalido")
    clientes = clientes.sort_values("id_cliente").reset_index(drop=True)
    clientes["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("clientes", len(clientes), int(duplicadas.sum()))

    cambios = contexto.fuentes["cambios_cliente"].copy()
    cambios["id_cliente"] = cambios["id_cliente"].str.strip().str.upper()
    cambios = cambios.sort_values(["id_cliente", "fecha_efectiva"]).reset_index(drop=True)
    if cambios.duplicated(["id_cliente", "fecha_efectiva"]).any():
        raise ValueError("Dos cambios cliente en igual fecha")
    if (
        not cambios["id_cliente"].isin(clientes["id_cliente"]).all()
        or not cambios["fecha_efectiva"].map(fecha_valida).all()
        or not cambios["nueva_region"].isin(REGIONES).all()
        or not cambios["nuevo_segmento"].isin(SEGMENTOS).all()
    ):
        raise ValueError("Cambio cliente invalido")
    inicios = clientes.set_index("id_cliente")["vigente_desde"].to_dict()
    if any(fila.fecha_efectiva <= inicios[fila.id_cliente] for fila in cambios.itertuples()):
        raise ValueError("Cambio no posterior al inicio cliente")
    cambios["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("cambios_cliente", len(cambios))
    return clientes, cambios
