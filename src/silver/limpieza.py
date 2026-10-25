"""Construcción de las siete entidades Silver sin claves sustitutas Gold."""
from __future__ import annotations

import pandas as pd

from ..comun.contratos import CONTRATOS
from ..comun.dominios import CATEGORIAS, REGIONES
from ..comun.utilidades import (
    clave_de_venta,
    es_entero,
    fecha_valida,
    importe_con_descuento,
    importe_proporcional,
)
from ..transformacion.contexto import recorrer_registros


SEGMENTOS = ["Ocasional", "Frecuente", "Preferente"]


def _intervalos_clientes(clientes: pd.DataFrame, cambios: pd.DataFrame) -> dict[str, list[tuple[str, str]]]:
    """Calcula vigencias naturales para validar ventas sin construir dim_cliente."""
    grupos = {clave: grupo for clave, grupo in cambios.groupby("id_cliente")}
    intervalos: dict[str, list[tuple[str, str]]] = {}
    for cliente in clientes.itertuples():
        desde = cliente.vigente_desde
        limites: list[tuple[str, str]] = []
        for cambio in grupos.get(cliente.id_cliente, pd.DataFrame()).itertuples():
            limites.append((desde, cambio.fecha_efectiva))
            desde = cambio.fecha_efectiva
        limites.append((desde, "9999-12-31"))
        intervalos[cliente.id_cliente] = limites
    return intervalos


def limpiar_clientes(contexto):
    clientes = contexto.fuentes["clientes"].copy()
    clientes["id_cliente"] = clientes["id_cliente"].str.strip().str.upper()
    clientes["correo"] = clientes["correo"].str.strip().str.lower()
    if clientes[CONTRATOS["clientes"].split()].eq("").any().any():
        raise ValueError("clientes: campo obligatorio vacio")
    duplicadas = clientes.duplicated(keep="first")
    for indice in clientes[duplicadas].index:
        contexto.duplicados.append(
            dict(
                fuente="clientes",
                fila_origen=int(indice) + 2,
                motivo="duplicado_identico_normalizado",
                id_ejecucion=contexto.id_ejecucion,
            )
        )
    clientes = clientes[~duplicadas].copy()
    if clientes["id_cliente"].duplicated().any() or clientes["correo"].duplicated().any():
        raise ValueError("Identidad cliente ambigua")
    if (
        not clientes["vigente_desde"].map(fecha_valida).all()
        or not clientes["region"].isin(REGIONES).all()
        or not clientes["segmento"].isin(SEGMENTOS).all()
    ):
        raise ValueError("Cliente invalido")
    clientes = clientes.sort_values("id_cliente").reset_index(drop=True)
    clientes["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("clientes", len(clientes), int(duplicadas.sum()))

    cambios = contexto.fuentes["cambios_cliente"].copy()
    cambios["id_cliente"] = cambios["id_cliente"].str.strip().str.upper()
    cambios = cambios.sort_values(["id_cliente", "fecha_efectiva"]).reset_index(drop=True)
    if cambios.duplicated(["id_cliente", "fecha_efectiva"]).any():
        raise ValueError("Dos cambios cliente en igual fecha")
    if (
        not cambios["id_cliente"].isin(clientes["id_cliente"]).all()
        or not cambios["fecha_efectiva"].map(fecha_valida).all()
        or not cambios["nueva_region"].isin(REGIONES).all()
        or not cambios["nuevo_segmento"].isin(SEGMENTOS).all()
    ):
        raise ValueError("Cambio cliente invalido")
    inicios = clientes.set_index("id_cliente")["vigente_desde"].to_dict()
    if any(fila.fecha_efectiva <= inicios[fila.id_cliente] for fila in cambios.itertuples()):
        raise ValueError("Cambio no posterior al inicio cliente")
    cambios["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("cambios_cliente", len(cambios))
    return clientes, cambios


def limpiar_productos(contexto):
    productos = contexto.fuentes["productos"].copy()
    productos["codigo_producto"] = productos["codigo_producto"].str.strip().str.upper()
    if productos[CONTRATOS["productos"].split()].eq("").any().any():
        raise ValueError("productos: campo obligatorio vacio")
    if productos["codigo_producto"].duplicated().any():
        raise ValueError("Clave maestra duplicada")
    for fila in productos.itertuples():
        if (
            fila.subcategoria not in CATEGORIAS.get(fila.categoria, [])
            or not es_entero(fila.costo_unitario)
            or not es_entero(fila.precio_lista)
            or int(fila.costo_unitario) <= 0
            or int(fila.precio_lista) <= 0
        ):
            raise ValueError("Producto invalido")
    for columna in ["costo_unitario", "precio_lista"]:
        productos[columna] = productos[columna].astype(int)
    productos = productos.sort_values("codigo_producto").reset_index(drop=True)
    productos["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("productos", len(productos))

    cambios = contexto.fuentes["cambios_producto"].copy()
    cambios["codigo_producto"] = cambios["codigo_producto"].str.strip().str.upper()
    cambios = cambios.sort_values(["fecha_efectiva", "codigo_producto"]).reset_index(drop=True)
    if cambios.duplicated(["codigo_producto", "fecha_efectiva", "tipo_cambio"]).any():
        raise ValueError("Cambio producto ambiguo")
    codigos = set(productos["codigo_producto"])
    for fila in cambios.itertuples():
        valido = fila.codigo_producto in codigos and fecha_valida(fila.fecha_efectiva)
        if fila.tipo_cambio == "correccion_nombre":
            valido = valido and bool(fila.nuevo_nombre) and not fila.nueva_categoria and not fila.nueva_subcategoria
        elif fila.tipo_cambio == "cambio_categoria":
            valido = valido and fila.nueva_subcategoria in CATEGORIAS.get(fila.nueva_categoria, [])
        else:
            valido = False
        if not valido:
            raise ValueError("Cambio producto invalido")
    cambios["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("cambios_producto", len(cambios))
    return productos, cambios


def limpiar_sucursales(contexto):
    sucursales = contexto.fuentes["sucursales"].copy()
    sucursales["codigo_sucursal"] = sucursales["codigo_sucursal"].str.strip().str.upper()
    if sucursales[["codigo_sucursal", "nombre_sucursal", "canal", "pais"]].eq("").any().any():
        raise ValueError("sucursales: campo obligatorio vacio")
    if sucursales["codigo_sucursal"].duplicated().any():
        raise ValueError("Clave maestra duplicada")
    if not sucursales["canal"].isin(["Tienda", "E-commerce"]).all():
        raise ValueError("Canal desconocido")
    for fila in sucursales.itertuples():
        if fila.canal == "Tienda" and (
            not fila.comuna
            or fila.region not in REGIONES
            or not -90 <= float(fila.latitud) <= 90
            or not -180 <= float(fila.longitud) <= 180
        ):
            raise ValueError("Geografia de tienda invalida")
    sucursales[["latitud", "longitud"]] = sucursales[["latitud", "longitud"]].apply(
        pd.to_numeric, errors="coerce"
    )
    sucursales = sucursales.sort_values("codigo_sucursal").reset_index(drop=True)
    sucursales["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("sucursales", len(sucursales))
    return sucursales


def limpiar_ventas(contexto, sucursales, productos, clientes, cambios_cliente):
    ventas = contexto.fuentes["ventas"].copy()
    for columna in [
        "sistema_origen",
        "id_comprobante",
        "id_cliente",
        "codigo_producto",
        "codigo_sucursal",
        "estado",
    ]:
        ventas[columna] = ventas[columna].str.strip().str.upper()
    ventas["clave_negocio"] = ventas.apply(clave_de_venta, axis=1)
    duplicadas = ventas.duplicated(CONTRATOS["ventas"].split(), keep="first")
    for indice in ventas[duplicadas].index:
        contexto.duplicados.append(
            dict(
                fuente="ventas",
                fila_origen=int(indice) + 2,
                motivo="duplicado_identico",
                id_ejecucion=contexto.id_ejecucion,
            )
        )
    unicas = ventas[~duplicadas].copy()
    conflictos = unicas["clave_negocio"].duplicated(keep=False)
    for indice, fila in unicas[conflictos].iterrows():
        contexto.rechazar("ventas", indice, fila, "conflicto_clave_negocio")
    unicas = unicas[~conflictos]

    codigos_producto = set(productos["codigo_producto"])
    canales = sucursales.set_index("codigo_sucursal")["canal"].to_dict()
    intervalos = _intervalos_clientes(clientes, cambios_cliente)
    validas = []
    for indice, fila in recorrer_registros(unicas):
        motivo = None
        obligatorios = [
            "sistema_origen",
            "id_comprobante",
            "numero_linea",
            "fecha_venta",
            "id_cliente",
            "codigo_producto",
            "codigo_sucursal",
            "estado",
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
            for columna in [
                "numero_linea",
                "cantidad",
                "precio_unitario",
                "porcentaje_descuento",
                "importe_bruto",
                "importe_tras_descuento",
            ]
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
        for columna in [
            "numero_linea",
            "cantidad",
            "precio_unitario",
            "porcentaje_descuento",
            "importe_bruto",
            "importe_tras_descuento",
        ]:
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
        ]
        .nunique()
        .gt(1)
        .any()
        .any()
    ):
        raise ValueError("Cabecera comprobante inconsistente")
    contexto.conciliar("ventas", len(resultado), int(duplicadas.sum()))
    return resultado


def limpiar_devoluciones(contexto, ventas):
    devoluciones = contexto.fuentes["devoluciones"].copy()
    for columna in ["id_devolucion", "sistema_origen", "id_comprobante"]:
        devoluciones[columna] = devoluciones[columna].str.strip().str.upper()
    devoluciones["clave_negocio"] = devoluciones.apply(clave_de_venta, axis=1)
    duplicadas = devoluciones.duplicated(CONTRATOS["devoluciones"].split(), keep="first")
    for indice in devoluciones[duplicadas].index:
        contexto.duplicados.append(
            dict(
                fuente="devoluciones",
                fila_origen=int(indice) + 2,
                motivo="duplicado_identico",
                id_ejecucion=contexto.id_ejecucion,
            )
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
            cantidad_acumulada,
            importe_previo + int(fila.importe_devuelto),
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


def preparar_tablas_silver(contexto):
    """Limpia maestros, eventos y transacciones; no construye tablas Gold."""
    clientes, cambios_cliente = limpiar_clientes(contexto)
    productos, cambios_producto = limpiar_productos(contexto)
    sucursales = limpiar_sucursales(contexto)
    ventas = limpiar_ventas(
        contexto, sucursales, productos, clientes, cambios_cliente
    )
    devoluciones = limpiar_devoluciones(contexto, ventas)
    tablas = {
        "clientes_limpios": clientes,
        "cambios_cliente_limpios": cambios_cliente,
        "productos_limpios": productos,
        "cambios_producto_limpios": cambios_producto,
        "sucursales_limpias": sucursales,
        "ventas_limpias": ventas,
        "devoluciones_limpias": devoluciones,
    }
    return tablas

