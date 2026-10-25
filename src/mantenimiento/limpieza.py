"""Limpieza por lista permitida; conserva fuentes, código y archivos ajenos."""
from pathlib import Path
from ..comun.bloqueo import BloqueoEjecucion
from ..silver.persistencia import limpiar_carpeta_silver, CARPETAS_SILVER

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVOS_SALIDA = (
    'dataretail360.sqlite', 'carga_temporal.sqlite', 'rechazos.csv',
    'resumen_ejecucion.json', 'resumen_ejecucion.json.tmp', 'ejecucion.log',
    'demostracion.sqlite', 'demostracion_temporal.sqlite', 'rechazos_demostracion.csv',
    'resumen_demostracion.json', 'resumen_demostracion.json.tmp', 'demostracion.log',
)


def limpiar_resultados(raiz=RAIZ):
    """Elimina únicamente una lista fija de salidas; nunca datos, código o entorno."""
    carpeta = Path(raiz).resolve() / 'resultados'
    bloqueo = BloqueoEjecucion(carpeta)
    eliminados = []
    try:
        # Comprobar todas las carpetas antes de borrar para proteger archivos ajenos.
        from ..silver.persistencia import comprobar_carpeta
        for nombre in sorted(CARPETAS_SILVER):
            comprobar_carpeta(carpeta / nombre)
        for nombre in ARCHIVOS_SALIDA:
            ruta = carpeta / nombre
            if ruta.is_symlink() or ruta.resolve().parent != carpeta.resolve():
                raise ValueError(f'Ruta de limpieza no permitida: {ruta}')
            if ruta.is_file():
                ruta.unlink()
                eliminados.append(nombre)
        for nombre in sorted(CARPETAS_SILVER):
            if (carpeta / nombre).exists():
                limpiar_carpeta_silver(carpeta / nombre)
                eliminados.append(nombre + '/')
    finally:
        bloqueo.cerrar()
    return eliminados
