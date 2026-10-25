# Arquitectura Bronze–Silver–Gold

## Bronze

`datos/entrada/` contiene los siete CSV oficiales y `manifiesto.json`. La
extracción lee todo como texto y valida columnas, cantidad de filas y SHA-256.
No corrige correos, no elimina duplicados y no crea claves analíticas.

## Silver

`src/silver/limpieza.py` produce siete entidades:

- `clientes_limpios`
- `cambios_cliente_limpios`
- `productos_limpios`
- `cambios_producto_limpios`
- `sucursales_limpias`
- `ventas_limpias`
- `devoluciones_limpias`

Las entidades usan identificadores naturales, fechas de negocio y tipos
explícitos. Silver valida duplicados, referencias, vigencias, importes y
devoluciones acumuladas. No contiene claves sustitutas, dimensiones ni hechos.

`src/silver/persistencia.py` escribe Parquet Snappy, auditoría y manifiesto en
un conjunto temporal, verifica la lectura de vuelta y publica mediante
intercambio seguro.

## Gold

`src/gold/construccion.py` solo recibe las entidades Silver reabiertas desde
disco. Allí se construyen:

- `dim_fecha`
- `dim_producto` con SCD 1 y SCD 3
- `dim_cliente` con SCD 2
- `dim_sucursal_canal`
- `hecho_ventas`
- `hecho_devoluciones`

Cada venta Silver debe producir exactamente un hecho y cada devolución Silver
debe resolver exactamente una venta Gold. Cualquier desacuerdo detiene la
publicación.

`src/carga/gold/` crea la base temporal, inserta dimensiones antes que hechos,
carga la auditoría, ejecuta controles SQL y publica SQLite solo si todos los
controles terminan en cero.

## Decisión sobre volumen y datos legibles

Se mantienen las 125.854 filas Bronze de ventas porque el procesamiento tarda
menos de un minuto y el volumen permite demostrar duplicados, referencias
desconocidas, fechas inválidas, medidas negativas y descuentos fuera de rango.
Reducirlo no mejora la ETL y haría perder la línea base.

Los nombres y correos son sintéticos. No se reemplazaron silenciosamente por
datos personales reales. `datos/muestra_calidad/clientes_muestra.csv` incorpora
nombres ficticios plausibles y correos deliberadamente inválidos o duplicados.
Se mantiene separado de las fuentes oficiales y se analiza en el notebook de
calidad, por lo que mejora la demostración sin cambiar la línea base.

