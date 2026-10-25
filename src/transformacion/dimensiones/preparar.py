"""Coordinación de las tres dimensiones maestras; las reglas viven en sus módulos."""
from .sucursales import preparar_sucursales
from .productos import preparar_productos
from .clientes import preparar_clientes


def preparar_dimensiones(contexto):
    """Reúne sucursales, productos, clientes y auditoría para el coordinador ETL."""
    sucursales = preparar_sucursales(contexto)
    productos, cambios = preparar_productos(contexto)
    clientes = preparar_clientes(contexto)
    return sucursales, productos, clientes, cambios
