"""Normalización, calidad y conciliación de devoluciones."""
import pandas as pd

from ..comun.contratos import CONTRATOS
from ..comun.utilidades import clave_de_venta, es_entero, fecha_valida, importe_proporcional
from ..transformacion.contexto import recorrer_registros


def limpiar_devoluciones(contexto, ventas):
    """Valida cada devolución contra su línea de venta en Silver."""
    devoluciones = contexto.fuentes["devoluciones"].copy()
    for columna in ["id_devolucion", "sistema_origen", "id_comprobante"]:
        devoluciones[columna] = devoluciones[columna].str.strip().str.upper()
    devoluciones["clave_negocio"] = devoluciones.apply(clave_de_venta, axis=1)
    duplicadas = devoluciones.duplicated(CONTRATOS["devoluciones"].split(), keep="first")
    for indice in devoluciones[duplicadas].index:
        contexto.duplicados.append(
            dict(fuente="devoluciones", fila_origen=int(indice) + 2,
                 motivo="duplicado_identico", id_ejecucion=contexto.id_ejecucion)
        )
    devoluciones = devoluciones[~duplicadas]
    conflictos = devoluciones["id_devolucion"].duplicated(keep=False)
    for indice, fila in devoluciones[conflictos].iterrows():
        contexto.rechazar("devoluciones", indice, fila, "conflicto_id_devolucion")

    ventas_por_clave = ventas.set_index("clave_negocio").to_dict("index")
    acumulados: dict[str, tuple[int, int]] = {}
    validas = []
    for indice, fila in recorrer_registros(
        devoluciones[~conflictos].sort_values(["fecha_devolucion", "id_devolucion"])
    ):
        venta = ventas_por_clave.get(fila.clave_negocio)
        motivo = None
        if not fila.id_devolucion or not fila.motivo:
            motivo = "campo_obligatorio_vacio"
        elif venta is None:
            motivo = "venta_no_encontrada"
        elif not fecha_valida(fila.fecha_devolucion):
            motivo = "fecha_devolucion_invalida"
        elif fila.fecha_devolucion < venta["fecha_venta"]:
            motivo = "devolucion_anterior_venta"
        elif not es_entero(fila.cantidad_devuelta) or not es_entero(fila.importe_devuelto):
            motivo = "valor_numerico_invalido"
        elif int(fila.cantidad_devuelta) <= 0 or int(fila.importe_devuelto) <= 0:
            motivo = "medida_devolucion_invalida"
        else:
            cantidad_previa, importe_previo = acumulados.get(fila.clave_negocio, (0, 0))
            cantidad_acumulada = cantidad_previa + int(fila.cantidad_devuelta)
            esperado = importe_proporcional(
                venta["importe_tras_descuento"], cantidad_acumulada, venta["cantidad"]
            ) - importe_proporcional(
                venta["importe_tras_descuento"], cantidad_previa, venta["cantidad"]
            )
            if cantidad_acumulada > venta["cantidad"]:
                motivo = "exceso_cantidad_devuelta"
            elif (
                int(fila.importe_devuelto) != esperado
                or importe_previo + int(fila.importe_devuelto) > venta["importe_tras_descuento"]
            ):
                motivo = "importe_devolucion_incoherente"
        if motivo:
            contexto.rechazar("devoluciones", indice, fila, motivo)
            continue
        acumulados[fila.clave_negocio] = (
            cantidad_acumulada, importe_previo + int(fila.importe_devuelto)
        )
        validas.append(
            dict(
                id_devolucion=fila.id_devolucion,
                clave_negocio=fila.clave_negocio,
                fecha_devolucion=fila.fecha_devolucion,
                cantidad_devuelta=int(fila.cantidad_devuelta),
                importe_devuelto=int(fila.importe_devuelto),
                motivo=fila.motivo,
                id_ejecucion=contexto.id_ejecucion,
            )
        )
    resultado = pd.DataFrame(validas).sort_values("id_devolucion").reset_index(drop=True)
    contexto.conciliar("devoluciones", len(resultado), int(duplicadas.sum()))
    return resultado
