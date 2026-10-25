"""Una sola implementación de la ETL, ejecutable completa o por etapas."""
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import uuid
import pandas as pd
from sqlalchemy import text
from .comun.bloqueo import BloqueoEjecucion
from .extraccion.preparar import extraer_fuentes
from .transformacion.contexto import ContextoTransformacion
from .transformacion.dimensiones.preparar import preparar_dimensiones
from .transformacion.ventas import preparar_ventas
from .transformacion.devoluciones import preparar_devoluciones
from .transformacion.conciliacion import armar_resultado
from .carga.gold.conexion import crear_motor
from .carga.gold.modelo import crear_modelo
from .carga.gold.dimensiones import cargar_dimensiones
from .carga.gold.hechos import cargar_hechos
from .carga.gold.auditoria import cargar_auditoria, registrar_ejecucion
from .carga.gold.validaciones import validar_carga
from .carga.gold.metricas import consultar_resultados
from .comun.utilidades import ahora, huella_archivo
from .carga.silver import guardar_silver, leer_silver

RAIZ = Path(__file__).resolve().parents[1]
ETAPAS = (
    'EXTRACCION', 'DIMENSIONES', 'VENTAS', 'DEVOLUCIONES', 'CONCILIACION',
    'GUARDAR_SILVER', 'LEER_SILVER', 'CONEXION', 'MODELO', 'CARGA_DIMENSIONES', 'CARGA_HECHOS', 'VALIDACION', 'PUBLICACION',
)


class SesionETL:
    """Cada método ejecuta exactamente una etapa; no avanza por sí solo.

    Las fuentes se conservan. La base temporal solo reemplaza la final al publicar.
    Los nombres de salida son fijos, por lo que no se acumulan archivos por corrida.
    """

    def __init__(self, raiz=RAIZ, modo='completo', carpeta_entrada=None):
        if modo not in ('completo', 'manual'):
            raise ValueError('Modo válido: completo o manual.')
        self.raiz = Path(raiz).resolve()
        self.entrada = Path(carpeta_entrada) if carpeta_entrada else self.raiz / 'datos' / 'entrada'
        self.salidas = self.raiz / 'resultados'
        self.bloqueo = BloqueoEjecucion(self.salidas)
        self.modo = modo
        self.id_ejecucion = 'ETL-' + uuid.uuid4().hex[:12]
        self.ruta_base = self.salidas / ('dataretail360.sqlite' if modo == 'completo' else 'demostracion.sqlite')
        self.ruta_temporal = self.salidas / ('carga_temporal.sqlite' if modo == 'completo' else 'demostracion_temporal.sqlite')
        self.ruta_resumen = self.salidas / ('resumen_ejecucion.json' if modo == 'completo' else 'resumen_demostracion.json')
        self.ruta_rechazos = self.salidas / ('rechazos.csv' if modo == 'completo' else 'rechazos_demostracion.csv')
        self.ruta_log = self.salidas / ('ejecucion.log' if modo == 'completo' else 'demostracion.log')
        self.carpeta_silver = self.salidas / ('silver' if modo == 'completo' else 'silver_demostracion')
        self.motor = None
        self.indice_etapa = 0
        self.terminada = False
        self.resultado = None
        self.resumen = {
            'id_ejecucion': self.id_ejecucion, 'modo': modo,
            'estrategia': 'reconstruccion_completa', 'estado': 'PREPARADA',
            'inicio': ahora(), 'base': str(self.ruta_base.relative_to(self.raiz)),
            'base_anterior_conservada': self.ruta_base.exists(), 'etapas': [],
        }
        self.logger = logging.getLogger(self.id_ejecucion)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.manejador = None
        try:
            if self.ruta_temporal.exists():
                self.ruta_temporal.unlink()
            self.manejador = logging.FileHandler(self.ruta_log, mode='w', encoding='utf-8')
            self.manejador.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
            self.logger.addHandler(self.manejador)
            pd.DataFrame(columns=['fuente', 'fila_origen', 'clave_origen', 'motivo', 'id_ejecucion', 'registro_original']).to_csv(self.ruta_rechazos, index=False, encoding='utf-8-sig')
            self.guardar_resumen()
        except BaseException:
            self.liberar_recursos()
            raise

    def guardar_resumen(self):
        """Sobrescribe el resumen de la última ejecución mediante reemplazo atómico."""
        temporal = self.ruta_resumen.with_suffix('.json.tmp')
        temporal.write_text(json.dumps(self.resumen, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporal, self.ruta_resumen)

    @contextmanager
    def paso(self, nombre):
        if self.terminada:
            raise RuntimeError('Sesión cerrada: crea otra sesión antes de volver a ejecutar.')
        esperada = ETAPAS[self.indice_etapa]
        if nombre != esperada:
            raise RuntimeError(f'Orden incorrecto: corresponde {esperada}, no {nombre}.')
        registro = {'etapa': nombre, 'inicio': ahora(), 'estado': 'EN_CURSO'}
        self.resumen['etapas'].append(registro)
        self.resumen['estado'] = 'EN_CURSO'
        self.logger.info('%s | INICIO', nombre)
        self.guardar_resumen()
        try:
            yield
        except BaseException as error:
            registro.update(estado='FALLIDA', fin=ahora(), error=str(error))
            self.resumen.update(estado='FALLIDA', fin=ahora(), etapa_fallida=nombre, error=str(error))
            self.logger.exception('%s | FALLIDA', nombre)
            try:
                self.guardar_resumen()
            finally:
                self.liberar_recursos()
            raise
        else:
            registro.update(estado='CORRECTA', fin=ahora())
            self.indice_etapa += 1
            self.logger.info('%s | CORRECTA', nombre)
            self.guardar_resumen()

    def extraer(self):
        """E: lee los siete CSV y comprueba columnas, conteos y huellas."""
        with self.paso('EXTRACCION'):
            self.fuentes, self.manifiesto, metadatos = extraer_fuentes(self.entrada, self.id_ejecucion)
            self.resumen['semilla'] = metadatos['semilla']
            self.resumen['datos_sinteticos'] = metadatos.get('datos_sinteticos', True)
            self.resumen['fuentes'] = self.manifiesto.drop(columns=['id_ejecucion']).to_dict('records')
        return self.fuentes

    def transformar_dimensiones(self):
        """T: normaliza maestros y construye dimensiones SCD 1, 2 y 3."""
        with self.paso('DIMENSIONES'):
            self.contexto = ContextoTransformacion(self.fuentes, self.id_ejecucion)
            self.sucursales, self.productos, self.clientes, self.cambios = preparar_dimensiones(self.contexto)
        return self.sucursales, self.productos, self.clientes

    def transformar_ventas(self):
        """T: valida líneas y resuelve claves y versión histórica del cliente."""
        with self.paso('VENTAS'):
            self.ventas = preparar_ventas(self.contexto, self.sucursales, self.productos, self.clientes)
        return self.ventas

    def transformar_devoluciones(self):
        """T: valida cada devolución contra las unidades y el importe pagados."""
        with self.paso('DEVOLUCIONES'):
            self.devoluciones = preparar_devoluciones(self.contexto, self.ventas)
        return self.devoluciones

    def conciliar(self):
        """T: explica cada fila y arma las seis tablas dimensionales en memoria."""
        with self.paso('CONCILIACION'):
            self.resultado = armar_resultado(self.contexto, self.sucursales, self.productos, self.clientes,
                                             self.ventas, self.devoluciones, self.cambios)
            self.tablas, rechazos, duplicados, conciliacion, _ = self.resultado
            if not conciliacion['diferencia'].eq(0).all():
                raise ValueError('No concilian las filas de entrada.')
            rechazos.to_csv(self.ruta_rechazos, index=False, encoding='utf-8-sig')
            self.resumen.update(
                filas_preparadas={nombre: len(datos) for nombre, datos in self.tablas.items()},
                filas_rechazadas=len(rechazos), filas_duplicadas=len(duplicados),
                conciliacion=conciliacion.to_dict('records'),
                rechazos_por_motivo=rechazos['motivo'].value_counts().to_dict(),
            )
        return self.resultado

    def conectar(self):
        """L: abre SQLite temporal. La base anterior todavía no se reemplaza."""
        with self.paso('CONEXION'):
            self.motor = crear_motor(self.ruta_temporal)
            with self.motor.connect() as conexion:
                conexion.execute(text('SELECT 1'))
        return self.motor

    def guardar_silver(self):
        """Persiste las seis tablas limpias en un conjunto Parquet verificado."""
        with self.paso('GUARDAR_SILVER'):
            self.manifiesto_silver = guardar_silver(self.tablas, self.carpeta_silver, self.id_ejecucion)
            self.resumen['silver'] = {
                'carpeta': str(self.carpeta_silver.relative_to(self.raiz)),
                'id_ejecucion': self.id_ejecucion, 'tablas': self.manifiesto_silver['tablas'],
            }
        return self.manifiesto_silver

    def leer_silver(self):
        """Vuelve a leer Parquet; estas tablas son las que se cargarán en Gold."""
        with self.paso('LEER_SILVER'):
            self.tablas, manifiesto = leer_silver(self.carpeta_silver, self.id_ejecucion)
            if manifiesto != self.manifiesto_silver:
                raise ValueError('El conjunto Silver cambió desde su escritura.')
            self.resultado = (self.tablas, *self.resultado[1:])
            self.resumen['gold_lee_desde_silver'] = True
        return self.tablas

    def crear_modelo(self):
        """L: crea dimensiones, hechos, auditoría, relaciones y vistas en español."""
        with self.paso('MODELO'):
            with self.motor.begin() as conexion:
                crear_modelo(conexion)

    def cargar_dimensiones(self):
        """L: inserta las dimensiones antes que los hechos para satisfacer las FK."""
        with self.paso('CARGA_DIMENSIONES'):
            with self.motor.begin() as conexion:
                cargar_dimensiones(conexion, self.tablas)

    def cargar_hechos(self):
        """L: inserta ventas, devoluciones y auditoría de esta ejecución."""
        with self.paso('CARGA_HECHOS'):
            with self.motor.begin() as conexion:
                cargar_hechos(conexion, self.tablas)
                cargar_auditoria(conexion, self.resultado, self.manifiesto)

    def validar(self):
        """Consulta SQLite: comprueba integridad, conteos, métricas y huellas."""
        with self.paso('VALIDACION'):
            with self.motor.connect() as conexion:
                controles = validar_carga(conexion, self.tablas, self.resultado[3])
                metricas, huellas = consultar_resultados(conexion, self.tablas)
            self.resumen.update(controles=controles, metricas=metricas, huellas_tablas=huellas)
        return controles

    def publicar(self, simular_fallo=False):
        """Publica solo la base validada. El fallo inyectado permite probar recuperación."""
        with self.paso('PUBLICACION'):
            _, manifiesto_silver = leer_silver(self.carpeta_silver, self.id_ejecucion)
            if manifiesto_silver != self.manifiesto_silver:
                raise ValueError('Silver cambió después de preparar Gold.')
            for fila in self.manifiesto.to_dict('records'):
                if huella_archivo(self.entrada / fila['archivo']) != fila['sha256']:
                    raise ValueError('Las fuentes cambiaron durante la ejecución.')
            with self.motor.begin() as conexion:
                registrar_ejecucion(conexion, self.id_ejecucion, self.modo,
                                    self.resumen['inicio'], ahora())
            self.motor.dispose()
            self.motor = None
            if simular_fallo:
                raise RuntimeError('Fallo de prueba antes de reemplazar la base.')
            os.replace(self.ruta_temporal, self.ruta_base)
            self.resumen.update(estado='CORRECTA', fin=ahora(), base_anterior_conservada=False)
        self.liberar_recursos()
        return self.resumen

    def consultar(self, sql):
        """Consulta de lectura para inspeccionar la base temporal en la demostración."""
        if self.motor is None:
            raise RuntimeError('Primero ejecuta conectar(); después de publicar, abre la base final.')
        with self.motor.connect() as conexion:
            return pd.read_sql_query(text(sql), conexion)

    def liberar_recursos(self):
        if self.terminada:
            return
        try:
            if self.motor is not None:
                self.motor.dispose()
                self.motor = None
            if self.ruta_temporal.exists():
                self.ruta_temporal.unlink()
        finally:
            if self.manejador is not None:
                self.manejador.close()
                self.logger.removeHandler(self.manejador)
            self.bloqueo.cerrar()
            self.terminada = True

    def cerrar(self):
        """Cancela una demostración incompleta sin publicar la base parcial."""
        if not self.terminada:
            self.resumen.update(estado='CANCELADA', fin=ahora())
            try:
                self.guardar_resumen()
            finally:
                self.liberar_recursos()

    def __enter__(self):
        return self

    def __exit__(self, tipo, error, traza):
        self.cerrar()


def ejecutar_completo(raiz=RAIZ, carpeta_entrada=None, simular_fallo=False, informar=print):
    """Ejecuta una carga, sin regenerar fuentes, correr pruebas ni crear informes."""
    with SesionETL(raiz, carpeta_entrada=carpeta_entrada) as sesion:
        for metodo in (sesion.extraer, sesion.transformar_dimensiones, sesion.transformar_ventas,
                       sesion.transformar_devoluciones, sesion.conciliar, sesion.guardar_silver,
                       sesion.leer_silver, sesion.conectar,
                       sesion.crear_modelo, sesion.cargar_dimensiones, sesion.cargar_hechos, sesion.validar):
            informar(f'Ejecutando: {metodo.__name__}')
            metodo()
        informar('Publicando la base validada...')
        return sesion.publicar(simular_fallo=simular_fallo)
