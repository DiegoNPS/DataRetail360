"""Selección de tablas finales y armado de la auditoría conciliada."""
import pandas as pd
from .dimensiones.fechas import preparar_fechas


def armar_resultado(contexto, sucursales_dimension, productos_dimension, clientes_dimension, ventas_validas, devoluciones_validas, auditoria_cambios):
    """Construye calendario y entrega hechos, dimensiones y auditoría conciliada."""
    rechazos = contexto.rechazos
    duplicados = contexto.duplicados
    conciliaciones = contexto.conciliaciones
    dimension_fecha = preparar_fechas(ventas_validas, devoluciones_validas)
    columnas_hechos = 'clave_venta clave_negocio sistema_origen id_comprobante numero_linea clave_fecha clave_producto clave_cliente clave_sucursal_canal cantidad precio_unitario porcentaje_descuento importe_bruto importe_descuento importe_tras_descuento id_ejecucion'.split()
    tablas = {'dim_fecha': dimension_fecha, 'dim_producto': productos_dimension, 'dim_cliente': clientes_dimension, 'dim_sucursal_canal': sucursales_dimension, 'hecho_ventas': ventas_validas[columnas_hechos], 'hecho_devoluciones': devoluciones_validas}
    return (tablas, pd.DataFrame(rechazos, columns=['fuente', 'fila_origen', 'clave_origen', 'motivo', 'id_ejecucion', 'registro_original']), pd.DataFrame(duplicados, columns=['fuente', 'fila_origen', 'motivo', 'id_ejecucion']), pd.DataFrame(conciliaciones), pd.DataFrame(auditoria_cambios))
