"""Validación del snapshot periódico de stock por producto y tienda."""
from ..comun.contratos import CONTRATOS
from ..comun.utilidades import es_entero, fecha_valida


def limpiar_stock(contexto, sucursales, productos):
    """Valida el grano fecha-producto-tienda y calcula medidas derivadas."""
    stock = contexto.fuentes["stock_diario"].copy()
    stock["codigo_producto"] = stock["codigo_producto"].str.strip().str.upper()
    stock["codigo_sucursal"] = stock["codigo_sucursal"].str.strip().str.upper()
    if stock[CONTRATOS["stock_diario"].split()].eq("").any().any():
        raise ValueError("stock_diario: campo obligatorio vacio")
    if stock.duplicated(["fecha_stock", "codigo_producto", "codigo_sucursal"]).any():
        raise ValueError("Stock duplicado en el mismo grano fecha-producto-tienda")

    codigos_producto = set(productos["codigo_producto"])
    tiendas = set(
        sucursales.loc[sucursales["canal"].eq("Tienda"), "codigo_sucursal"]
    )
    columnas_numericas = [
        "stock_fisico", "stock_reservado", "stock_en_transito", "costo_unitario"
    ]
    for fila in stock.itertuples():
        cantidades_validas = all(es_entero(getattr(fila, c)) for c in columnas_numericas)
        if (
            not fecha_valida(fila.fecha_stock)
            or fila.codigo_producto not in codigos_producto
            or fila.codigo_sucursal not in tiendas
            or not cantidades_validas
            or int(fila.stock_fisico) < 0
            or int(fila.stock_reservado) < 0
            or int(fila.stock_en_transito) < 0
            or int(fila.costo_unitario) <= 0
            or int(fila.stock_reservado) > int(fila.stock_fisico)
        ):
            raise ValueError("Registro de stock invalido")

    for columna in columnas_numericas:
        stock[columna] = stock[columna].astype(int)
    stock["stock_disponible"] = stock["stock_fisico"] - stock["stock_reservado"]
    stock["valor_stock"] = stock["stock_fisico"] * stock["costo_unitario"]
    stock = stock.sort_values(
        ["fecha_stock", "codigo_producto", "codigo_sucursal"]
    ).reset_index(drop=True)
    stock["id_ejecucion"] = contexto.id_ejecucion
    contexto.conciliar("stock_diario", len(stock))
    return stock
