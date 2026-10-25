"""Configuración del motor SQLite y de su integridad referencial."""
from pathlib import Path
from sqlalchemy import create_engine, event


def crear_motor(ruta):
    """Configura SQLite; cada conexión exige integridad de claves foráneas."""
    motor = create_engine('sqlite:///' + Path(ruta).resolve().as_posix())

    @event.listens_for(motor, 'connect')
    def activar_integridad(conexion, registro):
        conexion.execute('PRAGMA foreign_keys=ON')

    return motor
