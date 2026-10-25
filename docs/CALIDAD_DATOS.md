# Perfil de calidad de las fuentes oficiales

## Resumen

| Fuente | Filas | Hallazgos relevantes |
|---|---:|---|
| sucursales | 22 | 2 canales digitales sin geografía, condición permitida |
| productos | 1.000 | claves únicas y jerarquías válidas |
| clientes | 10.100 | 100 copias normalizadas; quedan 10.000 identidades |
| cambios_cliente | 2.000 | eventos SCD 2 válidos |
| cambios_producto | 50 | 30 correcciones SCD 1 y 20 reclasificaciones SCD 3 |
| ventas | 125.854 | 626 copias idénticas y errores deliberados |
| devoluciones | 4.618 | 1 copia idéntica y errores deliberados |

## Riesgos y tratamiento

- **Duplicados de venta:** 626 copias exactas y claves conflictivas controladas.
  Silver audita las copias y rechaza los conflictos.
- **Integridad:** existen filas deliberadas con cliente, producto o sucursal
  desconocidos. Se rechazan antes de Gold.
- **Fechas y medidas:** existe una fecha de venta inválida, una cantidad
  negativa, un precio vacío y un descuento de 120 %. Se conservan en Bronze y
  aparecen en la auditoría Silver.
- **Devoluciones:** existen eventos anteriores a la venta, sin venta aceptada o
  con acumulados incoherentes. Se rechazan sin alterar el hecho de venta.
- **Correos:** todos cumplen un patrón sintáctico básico y usan el dominio
  reservado `example.invalid`. Silver conserva la regla original: exige valor
  y unicidad, pero no simula la existencia del buzón.

## Controles automatizados

Las pruebas comprueban huellas Bronze, contrato Silver, ausencia de claves Gold
en Parquet, conciliación, conteos y métricas Gold, claves foráneas y seis vistas.
El notebook de calidad conserva el código y las tablas de evidencia.

## Muestra legible

`datos/muestra_calidad/clientes_muestra.csv` contiene 12 identidades ficticias
con nombres plausibles: 8 correos con formato válido, 3 mal formados, 1 vacío y
un valor repetido que afecta a 2 filas. Es una demostración separada; nunca se
mezcla con Bronze oficial.
