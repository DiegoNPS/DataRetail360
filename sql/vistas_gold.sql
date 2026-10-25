-- Las vistas consultan Gold sin crear copias adicionales de los hechos.
CREATE VIEW vista_detalle_ventas AS
SELECT v.*, f.fecha, f.anio, f.mes,
       p.codigo_producto, p.nombre_producto, p.marca, p.categoria, p.subcategoria,
       c.id_cliente, c.region AS region_cliente, c.segmento,
       s.codigo_sucursal, s.nombre_sucursal, s.canal, s.region AS region_sucursal
FROM hecho_ventas v
JOIN dim_fecha f USING(clave_fecha)
JOIN dim_producto p USING(clave_producto)
JOIN dim_cliente c USING(clave_cliente)
JOIN dim_sucursal_canal s USING(clave_sucursal_canal);

CREATE VIEW vista_detalle_devoluciones AS
SELECT d.*, fd.fecha AS fecha_devolucion, fv.fecha AS fecha_venta,
       v.clave_negocio AS clave_venta_origen, v.sistema_origen, v.id_comprobante, v.numero_linea,
       p.codigo_producto, p.nombre_producto, p.categoria, p.subcategoria,
       c.id_cliente, c.region AS region_cliente, c.segmento,
       s.codigo_sucursal, s.nombre_sucursal, s.canal
FROM hecho_devoluciones d
JOIN hecho_ventas v USING(clave_venta)
JOIN dim_fecha fd ON fd.clave_fecha=d.clave_fecha
JOIN dim_fecha fv ON fv.clave_fecha=v.clave_fecha
JOIN dim_producto p ON p.clave_producto=d.clave_producto
JOIN dim_cliente c ON c.clave_cliente=d.clave_cliente
JOIN dim_sucursal_canal s ON s.clave_sucursal_canal=d.clave_sucursal_canal;

-- Agregar devoluciones ANTES de unir evita duplicar una venta con varios eventos.
CREATE VIEW vista_ventas_netas AS
SELECT v.*, COALESCE(d.cantidad_devuelta,0) AS cantidad_devuelta,
       COALESCE(d.importe_devoluciones,0) AS importe_devoluciones,
       v.cantidad-COALESCE(d.cantidad_devuelta,0) AS cantidad_neta,
       v.importe_tras_descuento-COALESCE(d.importe_devoluciones,0) AS importe_neto
FROM vista_detalle_ventas v
LEFT JOIN (
    SELECT clave_venta, SUM(cantidad_devuelta) AS cantidad_devuelta,
           SUM(importe_devuelto) AS importe_devoluciones
    FROM hecho_devoluciones GROUP BY clave_venta
) d USING(clave_venta);

-- Actividad: cada hecho se reconoce en su propia fecha.
CREATE VIEW vista_actividad_mensual AS
SELECT f.anio, f.mes, s.canal,
       SUM(a.importe_bruto) AS ventas_brutas,
       SUM(a.importe_descuento) AS descuentos,
       SUM(a.ventas_tras_descuento) AS ventas_tras_descuento,
       SUM(a.importe_devuelto) AS devoluciones,
       SUM(a.ventas_tras_descuento)-SUM(a.importe_devuelto) AS ventas_netas
FROM (
    SELECT clave_fecha, clave_sucursal_canal, importe_bruto, importe_descuento,
           importe_tras_descuento AS ventas_tras_descuento, 0 AS importe_devuelto
    FROM hecho_ventas
    UNION ALL
    SELECT clave_fecha, clave_sucursal_canal, 0, 0, 0, importe_devuelto
    FROM hecho_devoluciones
) a
JOIN dim_fecha f USING(clave_fecha)
JOIN dim_sucursal_canal s USING(clave_sucursal_canal)
GROUP BY f.anio, f.mes, s.canal;

-- Cohorte de ventas: se descuentan todas sus devoluciones conocidas.
CREATE VIEW vista_ventas_por_producto AS
SELECT clave_producto, codigo_producto, nombre_producto, categoria, subcategoria,
       SUM(cantidad) AS unidades_vendidas,
       SUM(cantidad_devuelta) AS unidades_devueltas,
       SUM(cantidad_neta) AS unidades_netas,
       SUM(importe_bruto) AS ventas_brutas,
       SUM(importe_descuento) AS descuentos,
       SUM(importe_tras_descuento) AS ventas_tras_descuento,
       SUM(importe_devoluciones) AS devoluciones,
       SUM(importe_neto) AS ventas_netas
FROM vista_ventas_netas
GROUP BY clave_producto, codigo_producto, nombre_producto, categoria, subcategoria;

CREATE VIEW vista_ventas_por_sucursal AS
WITH totales AS (
    SELECT clave_sucursal_canal, codigo_sucursal, nombre_sucursal, canal, region_sucursal,
           SUM(cantidad) AS unidades_vendidas,
           SUM(cantidad_devuelta) AS unidades_devueltas,
           SUM(cantidad_neta) AS unidades_netas,
           SUM(importe_bruto) AS ventas_brutas,
           SUM(importe_descuento) AS descuentos,
           SUM(importe_tras_descuento) AS ventas_tras_descuento,
           SUM(importe_devoluciones) AS devoluciones,
           SUM(importe_neto) AS ventas_netas
    FROM vista_ventas_netas
    GROUP BY clave_sucursal_canal, codigo_sucursal, nombre_sucursal, canal, region_sucursal
), tickets AS (
    SELECT clave_sucursal_canal, COUNT(*) AS comprobantes
    FROM (
        SELECT clave_sucursal_canal, sistema_origen, id_comprobante
        FROM hecho_ventas
        GROUP BY clave_sucursal_canal, sistema_origen, id_comprobante
    ) GROUP BY clave_sucursal_canal
)
SELECT t.*, c.comprobantes,
       t.ventas_tras_descuento*1.0/c.comprobantes AS ticket_promedio_antes_devoluciones
FROM totales t JOIN tickets c USING(clave_sucursal_canal);
