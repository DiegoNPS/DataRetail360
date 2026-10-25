"""Dimensión de productos: limpieza, jerarquía y cambios SCD 1 y 3."""
from ...comun.contratos import CONTRATOS
from ...comun.utilidades import es_entero, fecha_valida
from ...comun.dominios import CATEGORIAS


def preparar_productos(contexto):
    """Devuelve productos preparados y la auditoría de sus cambios SCD."""
    fuentes = contexto.fuentes
    conciliar = contexto.conciliar
    productos_dimension = fuentes['productos'].copy()
    productos_dimension['codigo_producto'] = productos_dimension.codigo_producto.str.strip().str.upper()
    if productos_dimension[CONTRATOS['productos'].split()].eq('').any().any():
        raise ValueError('productos: campo obligatorio vacio')
    if productos_dimension.codigo_producto.duplicated().any():
        raise ValueError('Clave maestra duplicada')
    for registro in productos_dimension.itertuples():
        if registro.subcategoria not in CATEGORIAS.get(registro.categoria, []) or not es_entero(registro.costo_unitario) or (not es_entero(registro.precio_lista)) or (int(registro.costo_unitario) <= 0) or (int(registro.precio_lista) <= 0):
            raise ValueError('Producto invalido')
    conciliar('productos', len(productos_dimension))
    productos_dimension = productos_dimension.sort_values('codigo_producto').reset_index(drop=True)
    productos_dimension.insert(0, 'clave_producto', range(1, len(productos_dimension) + 1))
    productos_dimension['categoria_anterior'] = ''
    productos_dimension['subcategoria_anterior'] = ''
    productos_dimension['fecha_cambio_categoria'] = ''
    auditoria_cambios = []
    cambios_producto = fuentes['cambios_producto'].sort_values(['fecha_efectiva', 'codigo_producto'])
    if cambios_producto.duplicated(['codigo_producto', 'fecha_efectiva', 'tipo_cambio']).any():
        raise ValueError('Cambio producto ambiguo')
    for registro in cambios_producto.itertuples():
        if registro.codigo_producto not in set(productos_dimension.codigo_producto) or not fecha_valida(registro.fecha_efectiva):
            raise ValueError('Cambio producto invalido')
        indice = productos_dimension.index[productos_dimension.codigo_producto.eq(registro.codigo_producto)][0]
        if registro.tipo_cambio == 'correccion_nombre' and registro.nuevo_nombre:
            anterior = productos_dimension.at[indice, 'nombre_producto']
            productos_dimension.at[indice, 'nombre_producto'] = registro.nuevo_nombre
            auditoria_cambios.append(dict(codigo_producto=registro.codigo_producto, tipo_scd=1, valor_anterior=anterior, valor_nuevo=registro.nuevo_nombre, fecha_efectiva=registro.fecha_efectiva))
        elif registro.tipo_cambio == 'cambio_categoria' and registro.nueva_subcategoria in CATEGORIAS.get(registro.nueva_categoria, []):
            anterior = productos_dimension.at[indice, 'categoria'] + '/' + productos_dimension.at[indice, 'subcategoria']
            productos_dimension.at[indice, 'categoria_anterior'] = productos_dimension.at[indice, 'categoria']
            productos_dimension.at[indice, 'subcategoria_anterior'] = productos_dimension.at[indice, 'subcategoria']
            productos_dimension.at[indice, 'categoria'] = registro.nueva_categoria
            productos_dimension.at[indice, 'subcategoria'] = registro.nueva_subcategoria
            productos_dimension.at[indice, 'fecha_cambio_categoria'] = registro.fecha_efectiva
            auditoria_cambios.append(dict(codigo_producto=registro.codigo_producto, tipo_scd=3, valor_anterior=anterior, valor_nuevo=registro.nueva_categoria + '/' + registro.nueva_subcategoria, fecha_efectiva=registro.fecha_efectiva))
        else:
            raise ValueError('Cambio producto no soportado')
    conciliar('cambios_producto', len(cambios_producto))
    for columna in ['costo_unitario', 'precio_lista']:
        productos_dimension[columna] = productos_dimension[columna].astype(int)
    return productos_dimension, auditoria_cambios
