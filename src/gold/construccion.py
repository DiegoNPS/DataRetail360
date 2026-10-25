"""Construye dimensiones y hechos Gold desde las siete entidades Silver."""
from __future__ import annotations

import pandas as pd


def construir_dim_cliente(clientes, cambios):
    clientes = clientes.drop(columns=["id_ejecucion"], errors="ignore")
    cambios = cambios.drop(columns=["id_ejecucion"], errors="ignore")
    grupos = {clave: grupo for clave, grupo in cambios.groupby("id_cliente")}
    versiones = []
    for cliente in clientes.sort_values("id_cliente").itertuples():
        desde = cliente.vigente_desde
        region = cliente.region
        segmento = cliente.segmento
        for cambio in grupos.get(cliente.id_cliente, pd.DataFrame()).itertuples():
            versiones.append(
                (
                    cliente.id_cliente,
                    cliente.correo,
                    region,
                    segmento,
                    desde,
                    cambio.fecha_efectiva,
                    0,
                )
            )
            desde = cambio.fecha_efectiva
            region = cambio.nueva_region
            segmento = cambio.nuevo_segmento
        versiones.append(
            (cliente.id_cliente, cliente.correo, region, segmento, desde, "9999-12-31", 1)
        )
    dimension = pd.DataFrame(
        versiones,
        columns=[
            "id_cliente",
            "correo_normalizado",
            "region",
            "segmento",
            "vigente_desde",
            "vigente_hasta",
            "es_actual",
        ],
    )
    dimension.insert(0, "clave_cliente", range(1, len(dimension) + 1))
    return dimension


def construir_dim_producto(productos, cambios):
    dimension = (
        productos.drop(columns=["id_ejecucion"], errors="ignore")
        .sort_values("codigo_producto")
        .reset_index(drop=True)
    )
    dimension.insert(0, "clave_producto", range(1, len(dimension) + 1))
    dimension["categoria_anterior"] = ""
    dimension["subcategoria_anterior"] = ""
    dimension["fecha_cambio_categoria"] = ""
    auditoria = []
    for cambio in cambios.sort_values(["fecha_efectiva", "codigo_producto"]).itertuples():
        indice = dimension.index[
            dimension["codigo_producto"].eq(cambio.codigo_producto)
        ][0]
        if cambio.tipo_cambio == "correccion_nombre":
            anterior = dimension.at[indice, "nombre_producto"]
            dimension.at[indice, "nombre_producto"] = cambio.nuevo_nombre
            auditoria.append(
                dict(
                    codigo_producto=cambio.codigo_producto,
                    tipo_scd=1,
                    valor_anterior=anterior,
                    valor_nuevo=cambio.nuevo_nombre,
                    fecha_efectiva=cambio.fecha_efectiva,
                )
            )
        else:
            anterior = (
                dimension.at[indice, "categoria"]
                + "/"
                + dimension.at[indice, "subcategoria"]
            )
            dimension.at[indice, "categoria_anterior"] = dimension.at[indice, "categoria"]
            dimension.at[indice, "subcategoria_anterior"] = dimension.at[
                indice, "subcategoria"
            ]
            dimension.at[indice, "categoria"] = cambio.nueva_categoria
            dimension.at[indice, "subcategoria"] = cambio.nueva_subcategoria
            dimension.at[indice, "fecha_cambio_categoria"] = cambio.fecha_efectiva
            auditoria.append(
                dict(
                    codigo_producto=cambio.codigo_producto,
                    tipo_scd=3,
                    valor_anterior=anterior,
                    valor_nuevo=cambio.nueva_categoria + "/" + cambio.nueva_subcategoria,
                    fecha_efectiva=cambio.fecha_efectiva,
                )
            )
    return dimension, pd.DataFrame(auditoria)


def construir_dim_sucursal(sucursales):
    dimension = (
        sucursales.drop(columns=["id_ejecucion"], errors="ignore")
        .sort_values("codigo_sucursal")
        .reset_index(drop=True)
    )
    dimension.insert(0, "clave_sucursal_canal", range(1, len(dimension) + 1))
    return dimension


def construir_dim_fecha(ventas, devoluciones):
    fechas = list(ventas["fecha_venta"]) + list(devoluciones["fecha_devolucion"])
    inicio, fin = str(min(fechas))[:4], str(max(fechas))[:4]
    calendario = pd.date_range(inicio + "-01-01", fin + "-12-31")
    return pd.DataFrame(
        dict(
            clave_fecha=calendario.strftime("%Y%m%d").astype(int),
            fecha=calendario.strftime("%Y-%m-%d"),
            dia=calendario.day,
            mes=calendario.month,
            trimestre=calendario.quarter,
            anio=calendario.year,
        )
    )


def construir_hecho_ventas(ventas, productos, clientes, sucursales, id_ejecucion):
    claves_producto = productos.set_index("codigo_producto")["clave_producto"].to_dict()
    claves_sucursal = sucursales.set_index("codigo_sucursal")[
        "clave_sucursal_canal"
    ].to_dict()
    versiones = {
        clave: grupo.to_dict("records") for clave, grupo in clientes.groupby("id_cliente")
    }
    filas = []
    for venta in ventas.itertuples():
        candidatas = [
            version
            for version in versiones.get(venta.id_cliente, [])
            if version["vigente_desde"] <= venta.fecha_venta < version["vigente_hasta"]
        ]
        if len(candidatas) != 1:
            raise ValueError(
                f"Gold no resolvio una version unica para {venta.clave_negocio}"
            )
        if venta.codigo_producto not in claves_producto or venta.codigo_sucursal not in claves_sucursal:
            raise ValueError(f"Gold no resolvio dimensiones para {venta.clave_negocio}")
        filas.append(
            dict(
                clave_negocio=venta.clave_negocio,
                sistema_origen=venta.sistema_origen,
                id_comprobante=venta.id_comprobante,
                numero_linea=int(venta.numero_linea),
                clave_fecha=int(venta.fecha_venta.replace("-", "")),
                clave_producto=claves_producto[venta.codigo_producto],
                clave_cliente=candidatas[0]["clave_cliente"],
                clave_sucursal_canal=claves_sucursal[venta.codigo_sucursal],
                cantidad=int(venta.cantidad),
                precio_unitario=int(venta.precio_unitario),
                porcentaje_descuento=int(venta.porcentaje_descuento),
                importe_bruto=int(venta.importe_bruto),
                importe_descuento=int(venta.importe_descuento),
                importe_tras_descuento=int(venta.importe_tras_descuento),
                id_ejecucion=id_ejecucion,
            )
        )
    hechos = pd.DataFrame(filas).sort_values("clave_negocio").reset_index(drop=True)
    hechos.insert(0, "clave_venta", range(1, len(hechos) + 1))
    if len(hechos) != len(ventas):
        raise ValueError("No existe correspondencia uno a uno entre ventas Silver y Gold")
    return hechos


def construir_hecho_devoluciones(devoluciones, ventas, id_ejecucion):
    ventas_por_clave = ventas.set_index("clave_negocio").to_dict("index")
    filas = []
    for devolucion in devoluciones.itertuples():
        venta = ventas_por_clave.get(devolucion.clave_negocio)
        if venta is None:
            raise ValueError(
                f"Gold no encontro la venta de {devolucion.id_devolucion}"
            )
        filas.append(
            dict(
                id_devolucion=devolucion.id_devolucion,
                clave_venta=venta["clave_venta"],
                clave_fecha=int(devolucion.fecha_devolucion.replace("-", "")),
                clave_producto=venta["clave_producto"],
                clave_cliente=venta["clave_cliente"],
                clave_sucursal_canal=venta["clave_sucursal_canal"],
                cantidad_devuelta=int(devolucion.cantidad_devuelta),
                importe_devuelto=int(devolucion.importe_devuelto),
                motivo=devolucion.motivo,
                id_ejecucion=id_ejecucion,
            )
        )
    hechos = pd.DataFrame(filas).sort_values("id_devolucion").reset_index(drop=True)
    hechos.insert(0, "clave_devolucion", range(1, len(hechos) + 1))
    if len(hechos) != len(devoluciones):
        raise ValueError(
            "No existe correspondencia uno a uno entre devoluciones Silver y Gold"
        )
    return hechos


def construir_dimensiones_gold(tablas_silver):
    productos, cambios = construir_dim_producto(
        tablas_silver["productos_limpios"],
        tablas_silver["cambios_producto_limpios"],
    )
    clientes = construir_dim_cliente(
        tablas_silver["clientes_limpios"],
        tablas_silver["cambios_cliente_limpios"],
    )
    sucursales = construir_dim_sucursal(tablas_silver["sucursales_limpias"])
    fechas = construir_dim_fecha(
        tablas_silver["ventas_limpias"],
        tablas_silver["devoluciones_limpias"],
    )
    return {
        "dim_fecha": fechas,
        "dim_producto": productos,
        "dim_cliente": clientes,
        "dim_sucursal_canal": sucursales,
    }, cambios


def construir_hechos_gold(tablas_silver, dimensiones, id_ejecucion):
    ventas = construir_hecho_ventas(
        tablas_silver["ventas_limpias"],
        dimensiones["dim_producto"],
        dimensiones["dim_cliente"],
        dimensiones["dim_sucursal_canal"],
        id_ejecucion,
    )
    devoluciones = construir_hecho_devoluciones(
        tablas_silver["devoluciones_limpias"], ventas, id_ejecucion
    )
    return {"hecho_ventas": ventas, "hecho_devoluciones": devoluciones}

