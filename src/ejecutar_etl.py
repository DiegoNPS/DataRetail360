"""Entrada de consola: carga completa o limpieza controlada de salidas."""
import argparse
from .proceso import ejecutar_completo
from .mantenimiento.limpieza import limpiar_resultados


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limpiar', action='store_true', help='Borrar solo las salidas generadas')
    args = parser.parse_args()
    if args.limpiar:
        eliminados = limpiar_resultados()
        print('Resultados eliminados:', ', '.join(eliminados) or 'ninguno; ya estaba limpio')
        print('Se conservaron código, fuentes, documentación y entorno Python.')
        return
    resumen = ejecutar_completo()
    print('\nCARGA COMPLETA CORRECTA')
    print('Base:', resumen['base'])
    print('Silver Parquet:', resumen['silver']['carpeta'])
    print('Líneas de venta:', resumen['filas_preparadas']['hecho_ventas'])
    print('Devoluciones:', resumen['filas_preparadas']['hecho_devoluciones'])
    print('Venta neta sintética CLP:', resumen['metricas']['ventas_netas'])
    print('Los resultados anteriores fueron reemplazados tras validar la carga.')


if __name__ == '__main__':
    main()
