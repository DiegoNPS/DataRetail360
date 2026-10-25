# DataRetail360 — ETL Bronze, Silver y Gold

ETL reproducible de retail: CSV Bronze → entidades Parquet Silver → modelo
dimensional SQLite Gold. Los CSV oficiales no se regeneran ni se modifican.

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

1. **Bronze:** verifica los siete CSV, sus columnas, filas y SHA-256.
2. **Silver:** normaliza y valida maestros, cambios, ventas y devoluciones.
3. Guarda siete Parquet con claves de negocio más
   `auditoria_silver.json` y `manifiesto_silver.json`.
4. Descarta la copia en memoria y vuelve a leer Silver desde disco.
5. **Gold:** construye cuatro dimensiones, aplica SCD 1/2/3, resuelve dos
   hechos y exige correspondencia uno a uno con Silver.
6. Carga una SQLite temporal, crea seis vistas, valida y recién entonces
   reemplaza la base final.

## Resultados que se generan

- Ejecución completa: `resultados/dataretail360.sqlite` y `resultados/silver/`.
- Demostración manual: `resultados/demostracion.sqlite` y `resultados/silver_demostracion/`.
- Cada Silver contiene siete Parquet de entidades limpias, una auditoría y un
  manifiesto. No contiene `dim_*`, `hecho_*` ni claves sustitutas Gold.
- SQLite contiene cuatro dimensiones, dos hechos, seis vistas y seis tablas de
  auditoría.
- Logs, rechazos y resúmenes se guardan en `resultados/` con nombres fijos.

La ejecución reconstruye la base; no es incremental. Las salidas anteriores se reemplazan tras las validaciones correspondientes, sin acumular carpetas por corrida. Los CSV originales se conservan. La base final anterior se conserva si la nueva carga falla antes de publicarse.

## Contenido

| Carpeta o archivo | Función |
|---|---|
| `src/extraccion/` | Lectura y verificación Bronze |
| `src/silver/` | Limpieza, conciliación y persistencia de entidades |
| `src/gold/` | Construcción dimensional desde Silver leída |
| `src/carga/gold/` | Creación y carga de SQLite, validaciones y métricas |
| `sql/` | Creación de dimensiones, hechos, auditoría y vistas |
| `datos/entrada/` | Siete CSV sintéticos y su manifiesto |
| `notebooks/demostracion_etl.ipynb` | Ejecución manual de las etapas |
| `notebooks/analisis_calidad_datos.ipynb` | Perfil reproducible de las fuentes |
| `pruebas/` | Controles de separación de capas y equivalencia Gold |
| `requirements.txt` | Dependencias Python |
| Archivos `.cmd` | Preparación y accesos de ejecución |

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

La carga oficial validada produce 125.217 líneas de venta, 4.612 devoluciones
y venta neta sintética de $86.307.738.295 CLP. Son cifras de control del
conjunto incluido, no constantes usadas por el ETL.
