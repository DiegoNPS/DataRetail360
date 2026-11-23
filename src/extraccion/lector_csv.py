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
    """Lee una fuente y audita diferencias respecto del manifiesto de referencia.

    El manifiesto identifica la versión entregada, pero no inmoviliza Bronze para
    siempre. Una edición válida se carga y queda marcada como ``MODIFICADA``; los
    cambios ocurridos después de esta lectura se siguen bloqueando al publicar.
    """
    ruta = Path(carpeta_entrada) / f'{nombre}.csv'
    esperado = {fila['archivo']: fila for fila in manifiesto['archivos']}
    if ruta.name not in esperado:
        raise ValueError(f'Fuente no declarada en manifiesto: {nombre}')
    referencia = esperado[ruta.name]
    huella = huella_archivo(ruta)
    frame = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if set(frame.columns) != set(columnas.split()):
        raise ValueError(f'Contrato invalido: {nombre}')
    cambios = []
    if huella != referencia['sha256']:
        cambios.append('contenido')
    if len(frame) != referencia['filas']:
        cambios.append('filas')
    registro = {
        'archivo': ruta.name,
        'filas': len(frame),
        'sha256': huella,
        'filas_esperadas': referencia['filas'],
        'sha256_esperado': referencia['sha256'],
        'estado_fuente': 'MODIFICADA' if cambios else 'SIN_CAMBIOS',
        'detalle_cambio': ','.join(cambios),
        'id_ejecucion': id_ejecucion,
    }
    return frame, registro
