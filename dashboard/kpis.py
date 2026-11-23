"""Catálogo documentado de KPI del dashboard."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KPI:
    id: str
    nombre: str
    objetivo_negocio: str
    formula: str
    fuente: str
    unidad: str
    meta: str
    alerta: str
    dueno: str
    frecuencia: str
    tipo: str
    utilidad: str


CATALOGO_KPI = [
    KPI(
        "KPI-01", "Venta neta", "Medir los ingresos retenidos después de devoluciones.",
        "SUM(importe_tras_descuento) - SUM(importe_devoluciones)",
        "vista_ventas_netas.importe_tras_descuento, importe_devoluciones", "CLP",
        "≥ mismo período del año anterior", "< 90% del mismo período anterior",
        "Gerencia Comercial", "Mensual", "KPI de resultado",
        "Permite evaluar el desempeño comercial real sin sobrestimar ventas devueltas.",
    ),
    KPI(
        "KPI-02", "Crecimiento interanual de venta neta",
        "Detectar expansión o contracción respecto del período comparable.",
        "(venta_neta_actual - venta_neta_anterior) / venta_neta_anterior × 100",
        "vista_ventas_netas.fecha, importe_neto", "%", "≥ 0%", "≤ -10%",
        "Gerencia Comercial", "Mensual", "KPI de resultado",
        "Separa el tamaño absoluto de la venta de su evolución temporal.",
    ),
    KPI(
        "KPI-03", "Tasa de devoluciones", "Controlar pérdida de venta y posibles problemas de calidad.",
        "SUM(importe_devoluciones) / SUM(importe_tras_descuento) × 100",
        "vista_ventas_netas.importe_devoluciones, importe_tras_descuento", "%",
        "≤ 2%", "> 5%", "Jefatura de Experiencia de Cliente", "Mensual",
        "KPI de control", "Actúa como guardrail: crecer con devoluciones excesivas no es crecimiento sano.",
    ),
    KPI(
        "KPI-04", "Tasa de quiebre de stock", "Mantener productos disponibles en cada tienda.",
        "posiciones con stock_disponible = 0 / posiciones del último snapshot × 100",
        "vista_stock_tiendas.fecha_stock, stock_disponible", "%", "≤ 5%", "> 10%",
        "Jefatura de Operaciones", "Diaria", "KPI operativo",
        "Identifica pérdida potencial de venta y permite priorizar reposición por sucursal y producto.",
    ),
    KPI(
        "KPI-05", "Disponibilidad de inventario",
        "Vigilar qué proporción del inventario físico está libre para vender.",
        "SUM(stock_disponible) / SUM(stock_fisico) × 100 (último snapshot)",
        "vista_stock_tiendas.stock_disponible, stock_fisico", "%", "≥ 90%", "< 85%",
        "Jefatura de Operaciones", "Diaria", "KPI operativo",
        "Complementa el quiebre: muestra el efecto de reservas y disponibilidad global.",
    ),
]


def catalogo_como_filas():
    return [asdict(kpi) for kpi in CATALOGO_KPI]
