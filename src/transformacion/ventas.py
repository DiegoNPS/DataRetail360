"""Limpieza y validación de ventas y resolución de claves dimensionales."""
import pandas as pd
from ..comun.contratos import CONTRATOS
from ..comun.utilidades import es_entero, fecha_valida, importe_con_descuento, clave_de_venta
from .contexto import recorrer_registros


def preparar_ventas(contexto, sucursales_dimension, productos_dimension, clientes_dimension):
    """Valida líneas y resuelve claves dimensionales y versión temporal de cliente."""
    fuentes = contexto.fuentes
    id_ejecucion = contexto.id_ejecucion
    duplicados = contexto.duplicados
    rechazar = contexto.rechazar
    conciliar = contexto.conciliar
    ventas = fuentes['ventas'].copy()
    for columna in ['sistema_origen', 'id_comprobante', 'id_cliente', 'codigo_producto', 'codigo_sucursal', 'estado']:
        ventas[columna] = ventas[columna].str.strip().str.upper()
    ventas['clave_negocio'] = ventas.apply(clave_de_venta, axis=1)
    duplicadas = ventas.duplicated(CONTRATOS['ventas'].split(), keep='first')
    for indice in ventas[duplicadas].index:
        duplicados.append(dict(fuente='ventas', fila_origen=int(indice) + 2, motivo='duplicado_identico', id_ejecucion=id_ejecucion))
    ventas_unicas = ventas[~duplicadas].copy()
    conflictos = ventas_unicas.clave_negocio.duplicated(keep=False)
    for indice, fila in ventas_unicas[conflictos].iterrows():
        rechazar('ventas', indice, fila, 'conflicto_clave_negocio')
    ventas_unicas = ventas_unicas[~conflictos]
    validas = []
    claves_producto = dict(zip(productos_dimension.codigo_producto, productos_dimension.clave_producto))
    claves_sucursal = dict(zip(sucursales_dimension.codigo_sucursal, sucursales_dimension.clave_sucursal_canal))
    canales = dict(zip(sucursales_dimension.codigo_sucursal, sucursales_dimension.canal))
    versiones_por_cliente = {id_cliente_actual: grupo.to_dict('records') for id_cliente_actual, grupo in clientes_dimension.groupby('id_cliente')}
    for indice, fila in recorrer_registros(ventas_unicas):
        motivo = None
        if not all((fila[columna] for columna in ['sistema_origen', 'id_comprobante', 'numero_linea', 'fecha_venta', 'id_cliente', 'codigo_producto', 'codigo_sucursal', 'estado'])):
            motivo = 'campo_obligatorio_vacio'
        elif not fecha_valida(fila.fecha_venta):
            motivo = 'fecha_venta_invalida'
        elif fila.codigo_sucursal not in claves_sucursal:
            motivo = 'sucursal_desconocida'
        elif fila.codigo_producto not in claves_producto:
            motivo = 'producto_desconocido'
        elif fila.id_cliente not in versiones_por_cliente:
            motivo = 'cliente_desconocido'
        elif fila.estado != 'VALIDA':
            motivo = 'estado_no_admitido'
        elif fila.sistema_origen != ('POS' if canales[fila.codigo_sucursal] == 'Tienda' else 'ECOM'):
            motivo = 'origen_canal_incoherente'
        elif not all((es_entero(fila[columna]) for columna in ['numero_linea', 'cantidad', 'precio_unitario', 'porcentaje_descuento', 'importe_bruto', 'importe_tras_descuento'])):
            motivo = 'valor_numerico_invalido'
        elif int(fila.numero_linea) <= 0 or int(fila.cantidad) <= 0 or int(fila.precio_unitario) <= 0:
            motivo = 'medida_no_positiva'
        elif not 0 <= int(fila.porcentaje_descuento) <= 100:
            motivo = 'descuento_invalido'
        elif int(fila.importe_bruto) != int(fila.cantidad) * int(fila.precio_unitario) or int(fila.importe_tras_descuento) != importe_con_descuento(fila.importe_bruto, fila.porcentaje_descuento):
            motivo = 'importe_incoherente'
        else:
            version = [v for v in versiones_por_cliente[fila.id_cliente] if v['vigente_desde'] <= fila.fecha_venta < v['vigente_hasta']]
            if len(version) != 1:
                motivo = 'sin_version_cliente'
        if motivo:
            rechazar('ventas', indice, fila, motivo)
            continue
        salida = fila.to_dict()
        for columna in ['numero_linea', 'cantidad', 'precio_unitario', 'porcentaje_descuento', 'importe_bruto', 'importe_tras_descuento']:
            salida[columna] = int(salida[columna])
        salida.update(clave_cliente=version[0]['clave_cliente'], clave_producto=claves_producto[fila.codigo_producto], clave_sucursal_canal=claves_sucursal[fila.codigo_sucursal], clave_fecha=int(fila.fecha_venta.replace('-', '')), importe_descuento=salida['importe_bruto'] - salida['importe_tras_descuento'], id_ejecucion=id_ejecucion)
        validas.append(salida)
    ventas_validas = pd.DataFrame(validas)
    if ventas_validas.empty:
        raise ValueError('Ninguna venta valida')
    ventas_validas = ventas_validas.sort_values('clave_negocio').reset_index(drop=True)
    ventas_validas.insert(0, 'clave_venta', range(1, len(ventas_validas) + 1))
    conciliar('ventas', len(ventas_validas), int(duplicadas.sum()))
    if (ventas_validas.groupby(['sistema_origen', 'id_comprobante'])[['id_cliente', 'codigo_sucursal', 'fecha_venta']].nunique() > 1).any().any():
        raise ValueError('Cabecera comprobante inconsistente')
    return ventas_validas
