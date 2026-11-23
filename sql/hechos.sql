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

-- Snapshot periódico. Sus medidas son aditivas entre productos/tiendas para
-- una misma fecha, pero no deben sumarse entre fechas distintas.
CREATE TABLE hecho_stock_diario (
    clave_stock INTEGER PRIMARY KEY,
    clave_fecha INTEGER NOT NULL REFERENCES dim_fecha,
    clave_producto INTEGER NOT NULL REFERENCES dim_producto,
    clave_sucursal_canal INTEGER NOT NULL REFERENCES dim_sucursal_canal,
    stock_fisico INTEGER NOT NULL CHECK(stock_fisico>=0),
    stock_reservado INTEGER NOT NULL CHECK(stock_reservado>=0),
    stock_disponible INTEGER NOT NULL CHECK(stock_disponible>=0),
    stock_en_transito INTEGER NOT NULL CHECK(stock_en_transito>=0),
    costo_unitario INTEGER NOT NULL CHECK(costo_unitario>0),
    valor_stock INTEGER NOT NULL CHECK(valor_stock>=0),
    id_ejecucion TEXT NOT NULL,
    UNIQUE(clave_fecha,clave_producto,clave_sucursal_canal),
    CHECK(stock_reservado<=stock_fisico),
    CHECK(stock_disponible=stock_fisico-stock_reservado),
    CHECK(valor_stock=stock_fisico*costo_unitario)
);

CREATE INDEX indice_ventas_fecha ON hecho_ventas(clave_fecha);

CREATE INDEX indice_ventas_cliente ON hecho_ventas(clave_cliente);

CREATE INDEX indice_devoluciones_venta ON hecho_devoluciones(clave_venta);

CREATE INDEX indice_stock_fecha ON hecho_stock_diario(clave_fecha);

CREATE INDEX indice_stock_producto ON hecho_stock_diario(clave_producto);

CREATE INDEX indice_stock_tienda ON hecho_stock_diario(clave_sucursal_canal);
