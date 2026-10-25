"""Persistencia segura de siete entidades Silver y su auditoría."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from ..comun.utilidades import huella_archivo


ENTIDADES_SILVER = (
    "clientes_limpios",
    "cambios_cliente_limpios",
    "productos_limpios",
    "cambios_producto_limpios",
    "sucursales_limpias",
    "ventas_limpias",
    "devoluciones_limpias",
)
ARCHIVOS_SILVER = (
    {nombre + ".parquet" for nombre in ENTIDADES_SILVER}
    | {"manifiesto_silver.json", "auditoria_silver.json"}
)
ARCHIVOS_SILVER_ANTERIORES = {
    "dim_fecha.parquet",
    "dim_producto.parquet",
    "dim_cliente.parquet",
    "dim_sucursal_canal.parquet",
    "hecho_ventas.parquet",
    "hecho_devoluciones.parquet",
    "manifiesto_silver.json",
}
CARPETAS_SILVER = {
    "silver",
    "silver_temporal",
    "silver_anterior",
    "silver_demostracion",
    "silver_demostracion_temporal",
    "silver_demostracion_anterior",
}
VERSION_CONTRATO = 2


def comprobar_carpeta(carpeta):
    carpeta = Path(carpeta)
    if carpeta.name not in CARPETAS_SILVER:
        raise ValueError("Nombre de carpeta Silver no permitido.")
    if carpeta.is_symlink() or (
        hasattr(carpeta, "is_junction") and carpeta.is_junction()
    ):
        raise ValueError("Silver no puede ser un enlace o junction.")
    if carpeta.resolve().parent != carpeta.parent.resolve():
        raise ValueError("Silver debe permanecer dentro de resultados.")
    if carpeta.exists():
        if not carpeta.is_dir():
            raise ValueError("La ubicación Silver no es una carpeta.")
        for archivo in carpeta.iterdir():
            if (
                archivo.name not in (ARCHIVOS_SILVER | ARCHIVOS_SILVER_ANTERIORES)
                or archivo.is_symlink()
                or not archivo.is_file()
            ):
                raise ValueError(
                    f"Silver contiene un archivo ajeno; no se modifica: {archivo.name}"
                )
    return carpeta


def limpiar_carpeta_silver(carpeta):
    carpeta = comprobar_carpeta(carpeta)
    if carpeta.exists():
        for archivo in carpeta.iterdir():
            archivo.unlink()
        carpeta.rmdir()


def _leer_auditoria(carpeta, manifiesto):
    entrada = manifiesto["auditoria"]
    ruta = carpeta / entrada["archivo"]
    if huella_archivo(ruta) != entrada["sha256"]:
        raise ValueError("La auditoría Silver fue modificada.")
    auditoria = json.loads(ruta.read_text(encoding="utf-8"))
    if auditoria["id_ejecucion"] != manifiesto["id_ejecucion"]:
        raise ValueError("La auditoría Silver corresponde a otra ejecución.")
    return auditoria


def leer_silver(carpeta, id_ejecucion=None):
    """Lee Silver desde disco y valida contrato, huellas y auditoría."""
    carpeta = comprobar_carpeta(carpeta)
    ruta_manifiesto = carpeta / "manifiesto_silver.json"
    contenido_manifiesto = ruta_manifiesto.read_bytes()
    manifiesto = json.loads(contenido_manifiesto.decode("utf-8"))
    if manifiesto.get("version_contrato") != VERSION_CONTRATO:
        raise ValueError("Versión de contrato Silver incompatible.")
    if id_ejecucion is not None and manifiesto["id_ejecucion"] != id_ejecucion:
        raise ValueError("La Silver corresponde a otra ejecución.")
    entradas = manifiesto["entidades"]
    if len(entradas) != len(ENTIDADES_SILVER) or {
        fila["entidad"] for fila in entradas
    } != set(ENTIDADES_SILVER):
        raise ValueError("El manifiesto Silver no describe las siete entidades.")
    for fila in entradas:
        if fila["archivo"] != fila["entidad"] + ".parquet":
            raise ValueError("Nombre de archivo Silver inválido.")
        if huella_archivo(carpeta / fila["archivo"]) != fila["sha256"]:
            raise ValueError(f"Silver modificada o incompleta: {fila['archivo']}")
    tablas = {}
    for fila in entradas:
        datos = pd.read_parquet(carpeta / fila["archivo"], engine="pyarrow")
        if len(datos) != fila["filas"] or list(datos.columns) != fila["columnas"]:
            raise ValueError(
                f"Conteo o columnas Silver incorrectos: {fila['entidad']}"
            )
        if "id_ejecucion" in datos and not datos["id_ejecucion"].eq(
            manifiesto["id_ejecucion"]
        ).all():
            raise ValueError("Las filas Silver pertenecen a otra ejecución.")
        tablas[fila["entidad"]] = datos
    auditoria = _leer_auditoria(carpeta, manifiesto)
    if ruta_manifiesto.read_bytes() != contenido_manifiesto:
        raise ValueError("El manifiesto Silver cambió durante la lectura.")
    if any(
        huella_archivo(carpeta / fila["archivo"]) != fila["sha256"]
        for fila in entradas
    ):
        raise ValueError("Los Parquet Silver cambiaron durante la lectura.")
    return tablas, manifiesto, auditoria


def guardar_silver(tablas, auditoria, carpeta, id_ejecucion):
    """Escribe, verifica y publica el conjunto Silver completo."""
    destino = comprobar_carpeta(carpeta)
    temporal = comprobar_carpeta(destino.with_name(destino.name + "_temporal"))
    anterior = comprobar_carpeta(destino.with_name(destino.name + "_anterior"))
    if set(tablas) != set(ENTIDADES_SILVER):
        raise ValueError("Se deben preparar exactamente las siete entidades Silver.")
    if auditoria.get("id_ejecucion") != id_ejecucion:
        raise ValueError("La auditoría Silver corresponde a otra ejecución.")
    if anterior.exists():
        if destino.exists():
            try:
                leer_silver(destino)
            except (OSError, ValueError, KeyError):
                limpiar_carpeta_silver(destino)
                os.replace(anterior, destino)
            else:
                limpiar_carpeta_silver(anterior)
        else:
            os.replace(anterior, destino)
    limpiar_carpeta_silver(temporal)
    temporal.mkdir(parents=True)
    manifiesto = {
        "id_ejecucion": id_ejecucion,
        "version_contrato": VERSION_CONTRATO,
        "capa": "Silver",
        "formato": "Parquet",
        "motor": "pyarrow",
        "compresion": "snappy",
        "entidades": [],
    }
    try:
        for nombre in ENTIDADES_SILVER:
            datos = tablas[nombre]
            archivo = temporal / (nombre + ".parquet")
            datos.to_parquet(
                archivo, engine="pyarrow", compression="snappy", index=False
            )
            manifiesto["entidades"].append(
                {
                    "entidad": nombre,
                    "archivo": archivo.name,
                    "filas": len(datos),
                    "columnas": list(datos.columns),
                    "tipos_pandas": {
                        columna: str(tipo) for columna, tipo in datos.dtypes.items()
                    },
                    "sha256": huella_archivo(archivo),
                }
            )
        ruta_auditoria = temporal / "auditoria_silver.json"
        ruta_auditoria.write_text(
            json.dumps(auditoria, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifiesto["auditoria"] = {
            "archivo": ruta_auditoria.name,
            "sha256": huella_archivo(ruta_auditoria),
        }
        (temporal / "manifiesto_silver.json").write_text(
            json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        recuperadas, manifiesto_recuperado, auditoria_recuperada = leer_silver(
            temporal, id_ejecucion
        )
        for nombre in ENTIDADES_SILVER:
            pd.testing.assert_frame_equal(
                tablas[nombre].reset_index(drop=True),
                recuperadas[nombre],
                check_dtype=True,
            )
        if manifiesto_recuperado != manifiesto or auditoria_recuperada != auditoria:
            raise ValueError("La verificación de vuelta de Silver no coincide.")
        if destino.exists():
            os.replace(destino, anterior)
        try:
            os.replace(temporal, destino)
        except BaseException:
            if anterior.exists() and not destino.exists():
                os.replace(anterior, destino)
            raise
        limpiar_carpeta_silver(anterior)
    finally:
        limpiar_carpeta_silver(temporal)
    return manifiesto

