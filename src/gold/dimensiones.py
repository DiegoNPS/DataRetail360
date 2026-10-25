"""Construcción de las dimensiones Gold y tratamiento SCD."""
import pandas as pd


def construir_dim_cliente(clientes, cambios):
    clientes = clientes.drop(columns=["id_ejecucion"], errors="ignore")
    cambios = cambios.drop(columns=["id_ejecucion"], errors="ignore")
    grupos = {clave: grupo for clave, grupo in cambios.groupby("id_cliente")}
    versiones = []
    for cliente in clientes.sort_values("id_cliente").itertuples():
        desde, region, segmento = cliente.vigente_desde, cliente.region, cliente.segmento
        for cambio in grupos.get(cliente.id_cliente, pd.DataFrame()).itertuples():
            versiones.append((cliente.id_cliente, cliente.correo, region, segmento,
                              desde, cambio.fecha_efectiva, 0))
            desde, region, segmento = cambio.fecha_efectiva, cambio.nueva_region, cambio.nuevo_segmento
        versiones.append((cliente.id_cliente, cliente.correo, region, segmento,
                          desde, "9999-12-31", 1))
    dimension = pd.DataFrame(
        versiones,
        columns=["id_cliente", "correo_normalizado", "region", "segmento",
                 "vigente_desde", "vigente_hasta", "es_actual"],
    )
    dimension.insert(0, "clave_cliente", range(1, len(dimension) + 1))
    return dimension


def construir_dim_producto(productos, cambios):
    dimension = productos.drop(columns=["id_ejecucion"], errors="ignore").sort_values(
        "codigo_producto"
    ).reset_index(drop=True)
    dimension.insert(0, "clave_producto", range(1, len(dimension) + 1))
    dimension["categoria_anterior"] = ""
    dimension["subcategoria_anterior"] = ""
    dimension["fecha_cambio_categoria"] = ""
    auditoria = []
    for cambio in cambios.sort_values(["fecha_efectiva", "codigo_producto"]).itertuples():
        indice = dimension.index[dimension["codigo_producto"].eq(cambio.codigo_producto)][0]
        if cambio.tipo_cambio == "correccion_nombre":
            anterior = dimension.at[indice, "nombre_producto"]
            dimension.at[indice, "nombre_producto"] = cambio.nuevo_nombre
            tipo_scd = 1
            valor_nuevo = cambio.nuevo_nombre
        else:
            anterior = dimension.at[indice, "categoria"] + "/" + dimension.at[indice, "subcategoria"]
            dimension.at[indice, "categoria_anterior"] = dimension.at[indice, "categoria"]
            dimension.at[indice, "subcategoria_anterior"] = dimension.at[indice, "subcategoria"]
            dimension.at[indice, "categoria"] = cambio.nueva_categoria
            dimension.at[indice, "subcategoria"] = cambio.nueva_subcategoria
            dimension.at[indice, "fecha_cambio_categoria"] = cambio.fecha_efectiva
            tipo_scd = 3
            valor_nuevo = cambio.nueva_categoria + "/" + cambio.nueva_subcategoria
        auditoria.append(dict(codigo_producto=cambio.codigo_producto, tipo_scd=tipo_scd,
                              valor_anterior=anterior, valor_nuevo=valor_nuevo,
                              fecha_efectiva=cambio.fecha_efectiva))
    return dimension, pd.DataFrame(auditoria)


def construir_dim_sucursal(sucursales):
    dimension = sucursales.drop(columns=["id_ejecucion"], errors="ignore").sort_values(
        "codigo_sucursal"
    ).reset_index(drop=True)
    dimension.insert(0, "clave_sucursal_canal", range(1, len(dimension) + 1))
    return dimension


def construir_dim_fecha(ventas, devoluciones):
    fechas = list(ventas["fecha_venta"]) + list(devoluciones["fecha_devolucion"])
    inicio, fin = str(min(fechas))[:4], str(max(fechas))[:4]
    calendario = pd.date_range(inicio + "-01-01", fin + "-12-31")
    return pd.DataFrame(dict(clave_fecha=calendario.strftime("%Y%m%d").astype(int),
                             fecha=calendario.strftime("%Y-%m-%d"), dia=calendario.day,
                             mes=calendario.month, trimestre=calendario.quarter,
                             anio=calendario.year))
