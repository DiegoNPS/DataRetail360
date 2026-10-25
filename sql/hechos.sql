-- Hechos e índices. Crear después de las dimensiones.

CREATE TABLE hecho_ventas (
    clave_venta INTEGER PRIMARY KEY,
    clave_negocio TEXT UNIQUE NOT NULL,
    sistema_origen TEXT NOT NULL,
    id_comprobante TEXT NOT NULL,
    numero_linea INTEGER NOT NULL,
    clave_fecha INTEGER NOT NULL REFERENCES dim_fecha,
    clave_producto INTEGER NOT NULL REFERENCES dim_producto,
    clave_cliente INTEGER NOT NULL REFERENCES dim_cliente,
    clave_sucursal_canal INTEGER NOT NULL REFERENCES dim_sucursal_canal,
    cantidad INTEGER NOT NULL CHECK(cantidad>0),
    precio_unitario INTEGER NOT NULL CHECK(precio_unitario>0),
    porcentaje_descuento INTEGER NOT NULL CHECK(porcentaje_descuento BETWEEN 0 AND 100),
    importe_bruto INTEGER NOT NULL,
    importe_descuento INTEGER NOT NULL,
    importe_tras_descuento INTEGER NOT NULL CHECK(importe_tras_descuento>=0),
    id_ejecucion TEXT NOT NULL,
    CHECK(importe_bruto=cantidad*precio_unitario),
    CHECK(importe_bruto-importe_descuento=importe_tras_descuento)
);

CREATE TABLE hecho_devoluciones (
    clave_devolucion INTEGER PRIMARY KEY,
    id_devolucion TEXT UNIQUE NOT NULL,
    clave_venta INTEGER NOT NULL REFERENCES hecho_ventas,
    clave_fecha INTEGER NOT NULL REFERENCES dim_fecha,
    clave_producto INTEGER NOT NULL REFERENCES dim_producto,
    clave_cliente INTEGER NOT NULL REFERENCES dim_cliente,
    clave_sucursal_canal INTEGER NOT NULL REFERENCES dim_sucursal_canal,
    cantidad_devuelta INTEGER NOT NULL CHECK(cantidad_devuelta>0),
    importe_devuelto INTEGER NOT NULL CHECK(importe_devuelto>0),
    motivo TEXT NOT NULL,
    id_ejecucion TEXT NOT NULL
);

CREATE INDEX indice_ventas_fecha ON hecho_ventas(clave_fecha);

CREATE INDEX indice_ventas_cliente ON hecho_ventas(clave_cliente);

CREATE INDEX indice_devoluciones_venta ON hecho_devoluciones(clave_venta);
