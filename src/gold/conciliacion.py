"""Controles de correspondencia entre las entidades Silver y los hechos Gold."""


def conciliar_hechos(tablas_silver, hechos_gold):
    """Exige correspondencia uno a uno y devuelve los conteos auditables."""
    conteos = {
        "ventas_silver": len(tablas_silver["ventas_limpias"]),
        "ventas_gold": len(hechos_gold["hecho_ventas"]),
        "devoluciones_silver": len(tablas_silver["devoluciones_limpias"]),
        "devoluciones_gold": len(hechos_gold["hecho_devoluciones"]),
    }
    if conteos["ventas_silver"] != conteos["ventas_gold"]:
        raise ValueError("Ventas Silver y Gold no concilian.")
    if conteos["devoluciones_silver"] != conteos["devoluciones_gold"]:
        raise ValueError("Devoluciones Silver y Gold no concilian.")
    return conteos
