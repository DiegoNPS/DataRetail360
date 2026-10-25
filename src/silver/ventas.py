"""Normalización, calidad y conciliación de ventas."""
import pandas as pd

from ..comun.contratos import CONTRATOS
from ..comun.utilidades import clave_de_venta, es_entero, fecha_valida, importe_con_descuento
from ..transformacion.contexto import recorrer_registros
from .clientes import intervalos_clientes


def limpiar_ventas(contexto, sucursales, productos, clientes, cambios_cliente):
    """Valida el grano de venta y conserva solo claves naturales en Silver."""
    ventas = contexto.fuentes["ventas"].copy()
    for columna in [
        "sistema_origen", "id_comprobante", "id_cliente", "codigo_producto",
        "codigo_sucursal", "estado",
    ]:
        ventas[columna] = ventas[columna].str.strip().str.upper()
    ventas["clave_negocio"] = ventas.apply(clave_de_venta, axis=1)
    duplicadas = ventas.duplicated(CONTRATOS["ventas"].split(), keep="first")
    for indice in ventas[duplicadas].index:
        contexto.duplicados.append(
            dict(fuente="ventas", fila_origen=int(indice) + 2,
                 motivo="duplicado_identico", id_ejecucion=contexto.id_ejecucion)
        )
    unicas = ventas[~duplicadas].copy()
    conflictos = unicas["clave_negocio"].duplicated(keep=False)
    for indice, fila in unicas[conflictos].iterrows():
        contexto.rechazar("ventas", indice, fila, "conflicto_clave_negocio")
    unicas = unicas[~conflictos]

    codigos_producto = set(productos["codigo_producto"])
    canales = sucursales.set_index("codigo_sucursal")["canal"].to_dict()
    intervalos = intervalos_clientes(clientes, cambios_cliente)
    validas = []
    for indice, fila in recorrer_registros(unicas):
        motivo = None
        obligatorios = [
            "sistema_origen", "id_comprobante", "numero_linea", "fecha_venta",
            "id_cliente", "codigo_producto", "codigo_sucursal", "estado",
        ]
        if not all(fila[columna] for columna in obligatorios):
            motivo = "campo_obligatorio_vacio"
        elif not fecha_valida(fila.fecha_venta):
            motivo = "fecha_venta_invalida"
        elif fila.codigo_sucursal not in canales:
            motivo = "sucursal_desconocida"
        elif fila.codigo_producto not in codigos_producto:
            motivo = "producto_desconocido"
        elif fila.id_cliente not in intervalos:
            motivo = "cliente_desconocido"
        elif fila.estado != "VALIDA":
            motivo = "estado_no_admitido"
        elif fila.sistema_origen != ("POS" if canales[fila.codigo_sucursal] == "Tienda" else "ECOM"):
            motivo = "origen_canal_incoherente"
        elif not all(
            es_entero(fila[columna])
            for columna in ["numero_linea", "cantidad", "precio_unitario",
                            "porcentaje_descuento", "importe_bruto", "importe_tras_descuento"]
        ):
            motivo = "valor_numerico_invalido"
        elif int(fila.numero_linea) <= 0 or int(fila.cantidad) <= 0 or int(fila.precio_unitario) <= 0:
            motivo = "medida_no_positiva"
        elif not 0 <= int(fila.porcentaje_descuento) <= 100:
            motivo = "descuento_invalido"
        elif (
            int(fila.importe_bruto) != int(fila.cantidad) * int(fila.precio_unitario)
            or int(fila.importe_tras_descuento)
            != importe_con_descuento(fila.importe_bruto, fila.porcentaje_descuento)
        ):
            motivo = "importe_incoherente"
        elif sum(desde <= fila.fecha_venta < hasta for desde, hasta in intervalos[fila.id_cliente]) != 1:
            motivo = "sin_version_cliente"
        if motivo:
            contexto.rechazar("ventas", indice, fila, motivo)
            continue
        salida = fila.to_dict()
        for columna in ["numero_linea", "cantidad", "precio_unitario", "porcentaje_descuento",
                        "importe_bruto", "importe_tras_descuento"]:
            salida[columna] = int(salida[columna])
        salida["importe_descuento"] = salida["importe_bruto"] - salida["importe_tras_descuento"]
        salida["id_ejecucion"] = contexto.id_ejecucion
        validas.append(salida)
    resultado = pd.DataFrame(validas).sort_values("clave_negocio").reset_index(drop=True)
    if resultado.empty:
        raise ValueError("Ninguna venta valida")
    if (
        resultado.groupby(["sistema_origen", "id_comprobante"])[
            ["id_cliente", "codigo_sucursal", "fecha_venta"]
        ].nunique().gt(1).any().any()
    ):
        raise ValueError("Cabecera comprobante inconsistente")
    contexto.conciliar("ventas", len(resultado), int(duplicadas.sum()))
    return resultado
