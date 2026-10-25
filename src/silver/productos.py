"""Normalización y validación de productos y sus cambios."""
from ..comun.contratos import CONTRATOS
from ..comun.dominios import CATEGORIAS
from ..comun.utilidades import es_entero, fecha_valida


def limpiar_productos(contexto):
    """Depura el maestro de productos y valida eventos SCD 1 y 3."""
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
