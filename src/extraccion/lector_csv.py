"""Lectura CSV y comprobaciones técnicas comunes; no limpia datos de negocio."""
import json
from pathlib import Path
import pandas as pd
from ..comun.utilidades import huella_archivo


def leer_manifiesto(carpeta_entrada):
    """Lee una sola vez los metadatos declarados de las fuentes Bronze."""
    ruta = Path(carpeta_entrada) / 'manifiesto.json'
    return json.loads(ruta.read_text(encoding='utf-8'))


def leer_csv_validado(carpeta_entrada, nombre, columnas, manifiesto, id_ejecucion):
    """Lee una fuente como texto y devuelve su tabla cruda y su registro de auditoría."""
    ruta = Path(carpeta_entrada) / f'{nombre}.csv'
    esperado = {fila['archivo']: fila for fila in manifiesto['archivos']}
    huella = huella_archivo(ruta)
    if huella != esperado[ruta.name]['sha256']:
        raise ValueError(f'Bronze modificado: {nombre}')
    frame = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if set(frame.columns) != set(columnas.split()) or len(frame) != esperado[ruta.name]['filas']:
        raise ValueError(f'Contrato invalido: {nombre}')
    registro = {'archivo': ruta.name, 'filas': len(frame), 'sha256': huella, 'id_ejecucion': id_ejecucion}
    return frame, registro
