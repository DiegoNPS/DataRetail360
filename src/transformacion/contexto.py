"""Copias de trabajo, registros de filas y auditoría compartida de transformación."""
import json
from ..comun.utilidades import es_entero


class Registro(dict):
    """Registro liviano con acceso fila.campo y copia a dict."""
    __getattr__ = dict.__getitem__
    def to_dict(self):
        return dict(self)


def recorrer_registros(datos):
    """Itera filas conservando el índice físico del CSV."""
    return zip(datos.index, map(Registro, datos.to_dict('records')))


class ContextoTransformacion:
    """Estado de transformación: copias de entrada, rechazos y conciliación.

    Se comparte entre subetapas; no abre conexiones ni carga bases de datos.
    """

    def __init__(self, fuentes, id_ejecucion):
        self.fuentes_originales = fuentes
        self.fuentes = {nombre: frame.copy() for nombre, frame in fuentes.items()}
        self.id_ejecucion = id_ejecucion
        self.rechazos = []
        self.duplicados = []
        self.conciliaciones = []
        numericos = {'ventas': ['numero_linea', 'cantidad', 'precio_unitario', 'porcentaje_descuento', 'importe_bruto', 'importe_tras_descuento'], 'devoluciones': ['numero_linea', 'cantidad_devuelta', 'importe_devuelto'], 'productos': ['costo_unitario', 'precio_lista']}
        for nombre, columnas in numericos.items():
            for columna in columnas:
                self.fuentes[nombre][columna] = self.fuentes[nombre][columna].map(lambda valor: str(int(float(valor))) if es_entero(valor) else valor)

    def rechazar(self, fuente, indice, fila, motivo):
        self.rechazos.append({'fuente': fuente, 'fila_origen': int(indice) + 2, 'clave_origen': str(fila.get('id_devolucion', fila.get('clave_negocio', ''))), 'motivo': motivo, 'id_ejecucion': self.id_ejecucion, 'registro_original': json.dumps(self.fuentes_originales[fuente].loc[indice].to_dict(), ensure_ascii=False)})

    def conciliar(self, fuente, aceptadas, duplicadas=0):
        rechazadas = sum((fila['fuente'] == fuente for fila in self.rechazos))
        leidas = len(self.fuentes[fuente])
        self.conciliaciones.append({'fuente': fuente, 'filas_leidas': leidas, 'filas_aceptadas': aceptadas, 'filas_rechazadas': rechazadas, 'filas_duplicadas': duplicadas, 'diferencia': leidas - aceptadas - rechazadas - duplicadas})
