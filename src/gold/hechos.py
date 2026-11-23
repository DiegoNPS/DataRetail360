"""Construcción de hechos Gold y resolución de claves sustitutas."""
import pandas as pd


def construir_hecho_ventas(ventas, productos, clientes, sucursales, id_ejecucion):
    claves_producto = productos.set_index("codigo_producto")["clave_producto"].to_dict()
    claves_sucursal = sucursales.set_index("codigo_sucursal")["clave_sucursal_canal"].to_dict()
    versiones = {clave: grupo.to_dict("records") for clave, grupo in clientes.groupby("id_cliente")}
    filas = []
    for venta in ventas.itertuples():
        candidatas = [version for version in versiones.get(venta.id_cliente, [])
                      if version["vigente_desde"] <= venta.fecha_venta < version["vigente_hasta"]]
        if len(candidatas) != 1:
            raise ValueError(f"Gold no resolvio una version unica para {venta.clave_negocio}")
        if venta.codigo_producto not in claves_producto or venta.codigo_sucursal not in claves_sucursal:
            raise ValueError(f"Gold no resolvio dimensiones para {venta.clave_negocio}")
        filas.append(dict(
            clave_negocio=venta.clave_negocio, sistema_origen=venta.sistema_origen,
            id_comprobante=venta.id_comprobante, numero_linea=int(venta.numero_linea),
            clave_fecha=int(venta.fecha_venta.replace("-", "")),
            clave_producto=claves_producto[venta.codigo_producto],
            clave_cliente=candidatas[0]["clave_cliente"],
            clave_sucursal_canal=claves_sucursal[venta.codigo_sucursal],
            cantidad=int(venta.cantidad), precio_unitario=int(venta.precio_unitario),
            porcentaje_descuento=int(venta.porcentaje_descuento),
            importe_bruto=int(venta.importe_bruto), importe_descuento=int(venta.importe_descuento),
            importe_tras_descuento=int(venta.importe_tras_descuento), id_ejecucion=id_ejecucion,
        ))
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
            raise ValueError(f"Gold no encontro la venta de {devolucion.id_devolucion}")
        filas.append(dict(
            id_devolucion=devolucion.id_devolucion, clave_venta=venta["clave_venta"],
            clave_fecha=int(devolucion.fecha_devolucion.replace("-", "")),
            clave_producto=venta["clave_producto"], clave_cliente=venta["clave_cliente"],
            clave_sucursal_canal=venta["clave_sucursal_canal"],
            cantidad_devuelta=int(devolucion.cantidad_devuelta),
            importe_devuelto=int(devolucion.importe_devuelto), motivo=devolucion.motivo,
            id_ejecucion=id_ejecucion,
        ))
    hechos = pd.DataFrame(filas).sort_values("id_devolucion").reset_index(drop=True)
    hechos.insert(0, "clave_devolucion", range(1, len(hechos) + 1))
    if len(hechos) != len(devoluciones):
        raise ValueError("No existe correspondencia uno a uno entre devoluciones Silver y Gold")
    return hechos


def construir_hecho_stock(stock, productos, sucursales, id_ejecucion):
    """Resuelve el snapshot Silver al grano fecha-producto-tienda de Gold."""
    claves_producto = productos.set_index("codigo_producto")["clave_producto"].to_dict()
    claves_sucursal = sucursales.set_index("codigo_sucursal")["clave_sucursal_canal"].to_dict()
    filas = []
    for registro in stock.itertuples():
        if registro.codigo_producto not in claves_producto:
            raise ValueError(f"Gold no resolvio producto de stock {registro.codigo_producto}")
        if registro.codigo_sucursal not in claves_sucursal:
            raise ValueError(f"Gold no resolvio tienda de stock {registro.codigo_sucursal}")
        filas.append(
            dict(
                clave_fecha=int(registro.fecha_stock.replace("-", "")),
                clave_producto=claves_producto[registro.codigo_producto],
                clave_sucursal_canal=claves_sucursal[registro.codigo_sucursal],
                stock_fisico=int(registro.stock_fisico),
                stock_reservado=int(registro.stock_reservado),
                stock_disponible=int(registro.stock_disponible),
                stock_en_transito=int(registro.stock_en_transito),
                costo_unitario=int(registro.costo_unitario),
                valor_stock=int(registro.valor_stock),
                id_ejecucion=id_ejecucion,
            )
        )
    hechos = pd.DataFrame(filas).sort_values(
        ["clave_fecha", "clave_producto", "clave_sucursal_canal"]
    ).reset_index(drop=True)
    hechos.insert(0, "clave_stock", range(1, len(hechos) + 1))
    if len(hechos) != len(stock):
        raise ValueError("No existe correspondencia uno a uno entre stock Silver y Gold")
    return hechos
