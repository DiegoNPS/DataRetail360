# DataRetail360 — entrega de código

ETL de datos sintéticos: CSV Bronze → Parquet Silver → SQLite Gold.

## Preparación

1. Extraer todo el ZIP en una ruta corta, por ejemplo `C:\ETL`.
2. Entrar en la carpeta `DataRetail360` extraída.
3. Tener Python 3.12 o posterior instalado (probado con 3.12 y 3.14).
4. Ejecutar `PREPARAR_ENTORNO.cmd`. La primera preparación requiere Internet para instalar las dependencias de `requirements.txt` y crear el entorno local `.venv`.

## Ejecución

- **Carga completa:** ejecutar `EJECUTAR_COMPLETO.cmd`.
- **Demostración por etapas:** ejecutar `ABRIR_DEMOSTRACION.cmd`, seleccionar el kernel **Python - DataRetail360** y ejecutar las celdas del notebook en orden con Shift+Enter.
- **Reiniciar la prueba:** cerrar la sesión del notebook y ejecutar `LIMPIAR_RESULTADOS.cmd`. Conserva entradas y código. No es necesario limpiar para repetir una carga.

## Resultados que se generan

- Ejecución completa: `resultados/dataretail360.sqlite` y `resultados/silver/`.
- Demostración manual: `resultados/demostracion.sqlite` y `resultados/silver_demostracion/`.
- Cada Silver contiene seis Parquet y un manifiesto. SQLite contiene cuatro dimensiones, dos hechos, seis vistas y auditoría.
- Logs, rechazos y resúmenes se guardan en `resultados/` con nombres fijos.

La ejecución reconstruye la base; no es incremental. Las salidas anteriores se reemplazan tras las validaciones correspondientes, sin acumular carpetas por corrida. Los CSV originales se conservan. La base final anterior se conserva si la nueva carga falla antes de publicarse.

## Contenido

| Carpeta o archivo | Función |
|---|---|
| `src/` | Extracción, transformación, carga y mantenimiento |
| `sql/` | Creación de dimensiones, hechos, auditoría y vistas |
| `datos/entrada/` | Siete CSV sintéticos y su manifiesto |
| `notebooks/demostracion_etl.ipynb` | Ejecución manual de las etapas |
| `requirements.txt` | Dependencias Python |
| Archivos `.cmd` | Preparación y accesos de ejecución |

Se entregan fuentes y código; las bases de datos, Parquet y el entorno Python se crean al ejecutar. El paquete no incluye informe, presentación, documentación de estudio, pruebas ni respaldos.
