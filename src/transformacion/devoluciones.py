"""Validación de devoluciones contra las ventas aceptadas y sus acumulados."""
import pandas as pd
from ..comun.contratos import CONTRATOS
from ..comun.utilidades import es_entero, fecha_valida, importe_proporcional, clave_de_venta
from .contexto import recorrer_registros


def preparar_devoluciones(contexto, ventas_validas):
    """Valida eventos y cantidades e importes acumulados contra la venta original."""
    fuentes = contexto.fuentes
    id_ejecucion = contexto.id_ejecucion
    duplicados = contexto.duplicados
    rechazar = contexto.rechazar
    conciliar = contexto.conciliar
    devoluciones_fuente = fuentes['devoluciones'].copy()
    devoluciones_fuente['clave_negocio'] = devoluciones_fuente.apply(clave_de_venta, axis=1)
    duplicadas = devoluciones_fuente.duplicated(CONTRATOS['devoluciones'].split(), keep='first')
    for indice in devoluciones_fuente[duplicadas].index:
        duplicados.append(dict(fuente='devoluciones', fila_origen=int(indice) + 2, motivo='duplicado_identico', id_ejecucion=id_ejecucion))
    devoluciones_fuente = devoluciones_fuente[~duplicadas]
    conflictos = devoluciones_fuente.id_devolucion.duplicated(keep=False)
    for indice, fila in devoluciones_fuente[conflictos].iterrows():
        rechazar('devoluciones', indice, fila, 'conflicto_id_devolucion')
    ventas_por_clave = ventas_validas.set_index('clave_negocio').to_dict('index')
    acumulados = {}
    validas = []
    for indice, fila in recorrer_registros(devoluciones_fuente[~conflictos].sort_values(['fecha_devolucion', 'id_devolucion'])):
        venta = ventas_por_clave.get(fila.clave_negocio)
        motivo = None
        if not fila.id_devolucion or not fila.motivo:
            motivo = 'campo_obligatorio_vacio'
        elif venta is None:
            motivo = 'venta_no_encontrada'
        elif not fecha_valida(fila.fecha_devolucion):
            motivo = 'fecha_devolucion_invalida'
        elif fila.fecha_devolucion < venta['fecha_venta']:
            motivo = 'devolucion_anterior_venta'
        elif not es_entero(fila.cantidad_devuelta) or not es_entero(fila.importe_devuelto):
            motivo = 'valor_numerico_invalido'
        elif int(fila.cantidad_devuelta) <= 0 or int(fila.importe_devuelto) <= 0:
            motivo = 'medida_devolucion_invalida'
        else:
            cantidad_previa, importe_previo = acumulados.get(fila.clave_negocio, (0, 0))
            cantidad_acumulada = cantidad_previa + int(fila.cantidad_devuelta)
            esperado = importe_proporcional(venta['importe_tras_descuento'], cantidad_acumulada, venta['cantidad']) - importe_proporcional(venta['importe_tras_descuento'], cantidad_previa, venta['cantidad'])
            if cantidad_acumulada > venta['cantidad']:
                motivo = 'exceso_cantidad_devuelta'
            elif int(fila.importe_devuelto) != esperado or importe_previo + int(fila.importe_devuelto) > venta['importe_tras_descuento']:
                motivo = 'importe_devolucion_incoherente'
        if motivo:
            rechazar('devoluciones', indice, fila, motivo)
            continue
        acumulados[fila.clave_negocio] = (cantidad_acumulada, importe_previo + int(fila.importe_devuelto))
        validas.append(dict(id_devolucion=fila.id_devolucion, clave_venta=venta['clave_venta'], clave_fecha=int(fila.fecha_devolucion.replace('-', '')), clave_producto=venta['clave_producto'], clave_cliente=venta['clave_cliente'], clave_sucursal_canal=venta['clave_sucursal_canal'], cantidad_devuelta=int(fila.cantidad_devuelta), importe_devuelto=int(fila.importe_devuelto), motivo=fila.motivo, id_ejecucion=id_ejecucion))
    devoluciones_validas = pd.DataFrame(validas, columns=['id_devolucion', 'clave_venta', 'clave_fecha', 'clave_producto', 'clave_cliente', 'clave_sucursal_canal', 'cantidad_devuelta', 'importe_devuelto', 'motivo', 'id_ejecucion']).sort_values('id_devolucion').reset_index(drop=True)
    devoluciones_validas.insert(0, 'clave_devolucion', range(1, len(devoluciones_validas) + 1))
    conciliar('devoluciones', len(devoluciones_validas), int(duplicadas.sum()))
    return devoluciones_validas
