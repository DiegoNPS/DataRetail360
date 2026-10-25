"""Silver persistida: seis Parquet con un manifiesto que identifica el conjunto completo.

La sesión ETL mantiene el bloqueo global mientras escribe o lee. Se prepara una
carpeta temporal, se verifica el conjunto entero y recién entonces se reemplaza
la Silver anterior. Gold verifica huellas antes y después de leer los seis archivos.
"""
import json
import os
from pathlib import Path
import pandas as pd
from ..comun.utilidades import huella_archivo

TABLAS_SILVER = (
    'dim_fecha', 'dim_producto', 'dim_cliente', 'dim_sucursal_canal',
    'hecho_ventas', 'hecho_devoluciones',
)
ARCHIVOS_SILVER = {nombre + '.parquet' for nombre in TABLAS_SILVER} | {'manifiesto_silver.json'}
CARPETAS_SILVER = {
    'silver', 'silver_temporal', 'silver_anterior',
    'silver_demostracion', 'silver_demostracion_temporal', 'silver_demostracion_anterior',
}


def comprobar_carpeta(carpeta):
    """Impide mover o limpiar archivos ajenos y enlaces fuera de resultados."""
    carpeta = Path(carpeta)
    if carpeta.name not in CARPETAS_SILVER:
        raise ValueError('Nombre de carpeta Silver no permitido.')
    if carpeta.is_symlink() or (hasattr(carpeta, 'is_junction') and carpeta.is_junction()):
        raise ValueError('Silver no puede ser un enlace o junction.')
    if carpeta.resolve().parent != carpeta.parent.resolve():
        raise ValueError('Silver debe permanecer dentro de su carpeta de resultados.')
    if carpeta.exists():
        if not carpeta.is_dir():
            raise ValueError('La ubicación Silver no es una carpeta.')
        for archivo in carpeta.iterdir():
            if archivo.name not in ARCHIVOS_SILVER or archivo.is_symlink() or not archivo.is_file():
                raise ValueError(f'Silver contiene un archivo ajeno; no se modifica: {archivo.name}')
    return carpeta


def limpiar_carpeta_silver(carpeta):
    """Retira solo los seis Parquet y el manifiesto; sin borrado recursivo."""
    carpeta = comprobar_carpeta(carpeta)
    if carpeta.exists():
        for archivo in carpeta.iterdir():
            archivo.unlink()
        carpeta.rmdir()


def leer_silver(carpeta, id_ejecucion=None):
    """Lee una Silver completa y coherente desde disco, no desde los DataFrames previos."""
    carpeta = comprobar_carpeta(carpeta)
    ruta_manifiesto = carpeta / 'manifiesto_silver.json'
    contenido_manifiesto = ruta_manifiesto.read_bytes()
    manifiesto = json.loads(contenido_manifiesto.decode('utf-8'))
    if id_ejecucion is not None and manifiesto['id_ejecucion'] != id_ejecucion:
        raise ValueError('La Silver corresponde a otra ejecución.')
    entradas = manifiesto['tablas']
    if len(entradas) != len(TABLAS_SILVER) or {fila['tabla'] for fila in entradas} != set(TABLAS_SILVER):
        raise ValueError('El manifiesto Silver no describe las seis tablas esperadas.')
    for fila in entradas:
        if fila['archivo'] != fila['tabla'] + '.parquet':
            raise ValueError('Nombre de archivo Silver inválido.')
        if huella_archivo(carpeta / fila['archivo']) != fila['sha256']:
            raise ValueError(f'Silver modificada o incompleta: {fila["archivo"]}')
    tablas = {}
    for fila in entradas:
        datos = pd.read_parquet(carpeta / fila['archivo'], engine='pyarrow')
        if len(datos) != fila['filas'] or list(datos.columns) != fila['columnas']:
            raise ValueError(f'Conteo o columnas Silver incorrectos: {fila["tabla"]}')
        if 'id_ejecucion' in datos and not datos['id_ejecucion'].eq(manifiesto['id_ejecucion']).all():
            raise ValueError('Las filas Silver pertenecen a otra ejecución.')
        tablas[fila['tabla']] = datos
    # Detecta cambios durante la lectura, además de los detectados antes de abrir.
    if ruta_manifiesto.read_bytes() != contenido_manifiesto:
        raise ValueError('El manifiesto Silver cambió durante la lectura.')
    if any(huella_archivo(carpeta / fila['archivo']) != fila['sha256'] for fila in entradas):
        raise ValueError('Los Parquet Silver cambiaron durante la lectura.')
    return tablas, manifiesto


def guardar_silver(tablas, carpeta, id_ejecucion):
    """Escribe Snappy, verifica la ida y vuelta y publica el conjunto completo.

    Debe llamarse bajo el bloqueo de SesionETL. La carpeta anterior se conserva
    hasta terminar el intercambio y se recupera si una ejecución se interrumpe
    entre los dos renombrados. El manifiesto evita aceptar conjuntos mezclados.
    """
    destino = comprobar_carpeta(carpeta)
    temporal = comprobar_carpeta(destino.with_name(destino.name + '_temporal'))
    anterior = comprobar_carpeta(destino.with_name(destino.name + '_anterior'))
    if set(tablas) != set(TABLAS_SILVER):
        raise ValueError('Se deben preparar exactamente las seis tablas Silver.')
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
    manifiesto = {'id_ejecucion': id_ejecucion, 'formato': 'Parquet', 'motor': 'pyarrow',
                  'compresion': 'snappy', 'tablas': []}
    try:
        for nombre in TABLAS_SILVER:
            datos = tablas[nombre]
            archivo = temporal / (nombre + '.parquet')
            datos.to_parquet(archivo, engine='pyarrow', compression='snappy', index=False)
            manifiesto['tablas'].append({
                'tabla': nombre, 'archivo': archivo.name, 'filas': len(datos),
                'columnas': list(datos.columns),
                'tipos_pandas': {columna: str(tipo) for columna, tipo in datos.dtypes.items()},
                'sha256': huella_archivo(archivo),
            })
        (temporal / 'manifiesto_silver.json').write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding='utf-8')
        recuperadas, _ = leer_silver(temporal, id_ejecucion)
        for nombre in TABLAS_SILVER:
            pd.testing.assert_frame_equal(tablas[nombre].reset_index(drop=True), recuperadas[nombre], check_dtype=True)
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
