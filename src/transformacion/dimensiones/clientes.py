"""Dimensión de clientes: identidad normalizada y versiones históricas SCD 2."""
import pandas as pd
from ...comun.contratos import CONTRATOS
from ...comun.utilidades import fecha_valida
from ...comun.dominios import REGIONES


def preparar_clientes(contexto):
    """Normaliza clientes y devuelve sus versiones de región y segmento."""
    fuentes = contexto.fuentes
    id_ejecucion = contexto.id_ejecucion
    duplicados = contexto.duplicados
    conciliar = contexto.conciliar
    clientes_maestro = fuentes['clientes'].copy()
    clientes_maestro['id_cliente'] = clientes_maestro.id_cliente.str.strip().str.upper()
    clientes_maestro['correo'] = clientes_maestro.correo.str.strip().str.lower()
    if clientes_maestro[CONTRATOS['clientes'].split()].eq('').any().any():
        raise ValueError('clientes: campo obligatorio vacio')
    duplicadas = clientes_maestro.duplicated(keep='first')
    for indice in clientes_maestro[duplicadas].index:
        duplicados.append(dict(fuente='clientes', fila_origen=int(indice) + 2, motivo='duplicado_identico_normalizado', id_ejecucion=id_ejecucion))
    clientes_maestro = clientes_maestro[~duplicadas].copy()
    if clientes_maestro.id_cliente.duplicated().any() or clientes_maestro.correo.duplicated().any():
        raise ValueError('Identidad cliente ambigua')
    if not clientes_maestro.vigente_desde.map(fecha_valida).all() or not clientes_maestro.region.isin(REGIONES).all() or (not clientes_maestro.segmento.isin(['Ocasional', 'Frecuente', 'Preferente']).all()):
        raise ValueError('Cliente invalido')
    conciliar('clientes', len(clientes_maestro), int(duplicadas.sum()))
    cambios_cliente = fuentes['cambios_cliente'].sort_values(['id_cliente', 'fecha_efectiva'])
    if cambios_cliente.duplicated(['id_cliente', 'fecha_efectiva']).any():
        raise ValueError('Dos cambios cliente en igual fecha')
    if not cambios_cliente.id_cliente.isin(clientes_maestro.id_cliente).all() or not cambios_cliente.fecha_efectiva.map(fecha_valida).all() or (not cambios_cliente.nueva_region.isin(REGIONES).all()) or (not cambios_cliente.nuevo_segmento.isin(['Ocasional', 'Frecuente', 'Preferente']).all()):
        raise ValueError('Cambio cliente invalido')
    grupos = {id_cliente_actual: grupo for id_cliente_actual, grupo in cambios_cliente.groupby('id_cliente')}
    versiones = []
    for registro in clientes_maestro.sort_values('id_cliente').itertuples():
        desde = registro.vigente_desde
        region = registro.region
        segmento = registro.segmento
        if registro.id_cliente in grupos:
            for cambio in grupos[registro.id_cliente].itertuples():
                if cambio.fecha_efectiva <= desde:
                    raise ValueError('Cambio no posterior al inicio cliente')
                versiones.append((registro.id_cliente, registro.correo, region, segmento, desde, cambio.fecha_efectiva, 0))
                desde = cambio.fecha_efectiva
                region = cambio.nueva_region
                segmento = cambio.nuevo_segmento
        versiones.append((registro.id_cliente, registro.correo, region, segmento, desde, '9999-12-31', 1))
    clientes_dimension = pd.DataFrame(versiones, columns=['id_cliente', 'correo_normalizado', 'region', 'segmento', 'vigente_desde', 'vigente_hasta', 'es_actual'])
    clientes_dimension.insert(0, 'clave_cliente', range(1, len(clientes_dimension) + 1))
    conciliar('cambios_cliente', len(cambios_cliente))
    return clientes_dimension
