# DataRetail360 — ETL Bronze, Silver y Gold

ETL reproducible de retail: CSV Bronze → entidades Parquet Silver → modelo
dimensional SQLite Gold. La ETL no regenera ni modifica los CSV oficiales.

## Preparación

1. Extraer todo el ZIP en una ruta corta, por ejemplo `C:\ETL`.
2. Entrar en la carpeta `DataRetail360` extraída.
3. Tener Python 3.12 o posterior instalado (probado con 3.12 y 3.14).
4. Ejecutar `PREPARAR_ENTORNO.cmd`. La primera preparación requiere Internet para instalar las dependencias de `requirements.txt` y crear el entorno local `.venv`.

## Ejecución

- **Carga completa:** ejecutar `EJECUTAR_COMPLETO.cmd`.
- **Demostración por etapas:** ejecutar `ABRIR_DEMOSTRACION.cmd`, seleccionar el kernel **Python - DataRetail360** y ejecutar las celdas del notebook en orden con Shift+Enter.
- **Reiniciar la prueba:** cerrar la sesión del notebook y ejecutar `LIMPIAR_RESULTADOS.cmd`. Conserva entradas y código. No es necesario limpiar para repetir una carga.

## Orden real de ejecución

1. **Bronze:** valida los ocho CSV y compara filas/SHA-256 con el manifiesto de referencia. Una edición válida se carga con advertencia y auditoría; una ruptura de columnas se rechaza.
2. **Silver:** normaliza y valida maestros, cambios, ventas, devoluciones y stock.
3. Guarda ocho Parquet con claves de negocio más
   `auditoria_silver.json` y `manifiesto_silver.json`.
4. Descarta la copia en memoria y vuelve a leer Silver desde disco.
5. **Gold:** construye cuatro dimensiones, aplica SCD 1/2/3, resuelve tres
   hechos y exige correspondencia uno a uno con Silver.
6. Carga una SQLite temporal, crea siete vistas, valida y recién entonces
   reemplaza la base final.

## Resultados que se generan

- Ejecución completa: `resultados/dataretail360.sqlite` y `resultados/silver/`.
- Demostración manual: `resultados/demostracion.sqlite` y `resultados/silver_demostracion/`.
- Cada Silver contiene ocho Parquet de entidades limpias, una auditoría y un
  manifiesto. No contiene `dim_*`, `hecho_*` ni claves sustitutas Gold.
- SQLite contiene cuatro dimensiones, tres hechos, siete vistas y siete tablas de
  auditoría.
- Logs, rechazos y resúmenes se guardan en `resultados/` con nombres fijos.

La ejecución reconstruye la base; no es incremental. Las salidas anteriores se reemplazan tras las validaciones correspondientes, sin acumular carpetas por corrida. Los CSV originales se conservan. La base final anterior se conserva si la nueva carga falla antes de publicarse.

## Control de cambios de fuentes y clientes

- `manifiesto.json` es la línea base de la entrega, no un bloqueo permanente. `etl_fuentes` guarda filas y SHA-256 esperados/observados, el estado `SIN_CAMBIOS` o `MODIFICADA` y el detalle de la diferencia.
- Si un archivo cambia antes de iniciar la ETL, la consola y el log emiten un aviso; el contrato de columnas y las reglas de calidad siguen siendo obligatorios.
- Si un archivo cambia mientras la ETL está en curso, la publicación se detiene para evitar una base construida con versiones mezcladas.
- Un correo modificado respecto de la última Gold publicada se aplica como SCD tipo 1. `etl_cambios_cliente` conserva cliente, valor anterior, valor nuevo, ejecución y fecha de detección. También audita altas y bajas, y su historial sobrevive a las reconstrucciones completas.
- La primera carga establece la línea base y no registra falsamente a todos los clientes como altas.

## Contenido

| Carpeta o archivo | Función |
|---|---|
| `src/extraccion/` | Lectura y verificación Bronze |
| `src/silver/` | Pipeline, módulos por entidad y persistencia Silver |
| `src/gold/` | Pipeline, dimensiones, hechos y conciliación Gold |
| `src/carga/gold/` | Creación y carga de SQLite, validaciones y métricas |
| `sql/` | Creación de dimensiones, hechos, auditoría y vistas |
| `datos/entrada/` | Ocho CSV sintéticos y su manifiesto |
| `notebooks/demostracion_etl.ipynb` | Ejecución manual de las etapas |
| `notebooks/analisis_calidad_datos.ipynb` | Perfil reproducible de las fuentes |
| `pruebas/` | Controles de capas, equivalencia Gold, recuperación y cambios Bronze/cliente |
| `requirements.txt` | Dependencias Python |
| Archivos `.cmd` | Preparación y accesos de ejecución |

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

La carga oficial validada produce 125.217 líneas de venta, 4.612 devoluciones,
20.000 snapshots de stock y venta neta sintética de $86.307.738.295 CLP. Son cifras de control del
conjunto incluido, no constantes usadas por el ETL.

## Hecho de stock de tiendas

`hecho_stock_diario` es un snapshot periódico con grano fecha-producto-tienda.
La fuente inicial contiene el cierre del 31-12-2025 para 1.000 productos en 20
tiendas físicas. Registra stock físico, reservado, disponible, en tránsito,
costo unitario y valor del stock. Estas medidas pueden sumarse entre productos
o tiendas para una misma fecha, pero no entre fechas diferentes. La vista
`vista_stock_tiendas` agrega los atributos descriptivos y clasifica cada posición
como `AGOTADO`, `CRITICO`, `BAJO` o `DISPONIBLE`.

## Nueva versión de correos sintéticos

Las fuentes de esta versión tienen correos de dominios variados y ocho clientes adicionales con correos inválidos para demostrar rechazos. Se actualizó el manifiesto de entrada de forma explícita. Véase `docs/VALIDACION_CORREOS.md`. Las ventas y sus importes se conservan. Los notebooks se entregan sin salidas antiguas: ejecutarlos para generar la evidencia actual.
