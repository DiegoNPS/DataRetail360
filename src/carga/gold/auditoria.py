"""Trazabilidad de fuentes, rechazos, duplicados y ejecuciones publicadas."""
from sqlalchemy import text
from .insercion import cargar_tablas


def cargar_auditoria(conexion, resultado, manifiesto):
    """Guarda la trazabilidad en SQLite en lugar de exportar muchos archivos."""
    _, rechazos, duplicados, conciliacion, cambios = resultado
    for nombre, datos in {
        'etl_rechazos': rechazos,
        'etl_duplicados': duplicados,
        'etl_conciliacion': conciliacion,
        'etl_cambios_producto': cambios,
        'etl_fuentes': manifiesto,
    }.items():
        # Una fuente sin eventos conserva su tabla vacía, definida por el DDL.
        if not datos.empty:
            cargar_tablas(conexion, {nombre: datos}, (nombre,))


def registrar_ejecucion(conexion, id_ejecucion, modo, inicio, fin):
    """Registra el éxito únicamente al publicar una base ya validada."""
    conexion.execute(text('''
        INSERT INTO etl_ejecuciones(id_ejecucion,modo,estrategia,inicio,fin,estado)
        VALUES(:id,:modo,:estrategia,:inicio,:fin,:estado)
    '''), {'id': id_ejecucion, 'modo': modo, 'estrategia': 'reconstruccion_completa',
           'inicio': inicio, 'fin': fin, 'estado': 'CORRECTA'})
