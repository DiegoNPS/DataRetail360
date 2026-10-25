"""Impide cargas y limpiezas concurrentes sin dejar bloqueos huérfanos."""
import os


class BloqueoEjecucion:
    """Bloqueo del sistema operativo: se libera aunque el proceso termine."""

    def __init__(self, carpeta):
        carpeta.mkdir(parents=True, exist_ok=True)
        if carpeta.is_symlink():
            raise ValueError('La carpeta resultados no puede ser un enlace simbólico.')
        self.archivo = (carpeta / '.etl.lock').open('a+b')
        self.archivo.seek(0, 2)
        if self.archivo.tell() == 0:
            self.archivo.write(b'0')
            self.archivo.flush()
        self.archivo.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.archivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.archivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.archivo.close()
            raise RuntimeError('Ya hay una ETL o demostración abierta. Cierra esa sesión antes de cargar o limpiar.') from error
        self.cerrado = False

    def cerrar(self):
        if self.cerrado:
            return
        self.archivo.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.archivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.archivo.fileno(), fcntl.LOCK_UN)
        finally:
            self.archivo.close()
            self.cerrado = True
