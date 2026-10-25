-- Cuatro dimensiones e índice de versión actual de cliente.

CREATE TABLE dim_fecha (
    clave_fecha INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL UNIQUE,
    dia INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    anio INTEGER NOT NULL
);

CREATE TABLE dim_producto (
    clave_producto INTEGER PRIMARY KEY,
    codigo_producto TEXT NOT NULL UNIQUE,
    nombre_producto TEXT NOT NULL,
    marca TEXT NOT NULL,
    categoria TEXT NOT NULL,
    subcategoria TEXT NOT NULL,
    costo_unitario INTEGER NOT NULL,
    precio_lista INTEGER NOT NULL,
    categoria_anterior TEXT,
    subcategoria_anterior TEXT,
    fecha_cambio_categoria TEXT
);

CREATE TABLE dim_cliente (
    clave_cliente INTEGER PRIMARY KEY,
    id_cliente TEXT NOT NULL,
    correo_normalizado TEXT NOT NULL,
    region TEXT NOT NULL,
    segmento TEXT NOT NULL,
    vigente_desde TEXT NOT NULL,
    vigente_hasta TEXT NOT NULL,
    es_actual INTEGER NOT NULL CHECK(es_actual IN (0,1)),
    UNIQUE(id_cliente,vigente_desde),
    CHECK(vigente_desde<vigente_hasta)
);

CREATE UNIQUE INDEX unico_cliente_actual ON dim_cliente(id_cliente) WHERE es_actual=1;

CREATE TABLE dim_sucursal_canal (
    clave_sucursal_canal INTEGER PRIMARY KEY,
    codigo_sucursal TEXT NOT NULL UNIQUE,
    nombre_sucursal TEXT NOT NULL,
    canal TEXT NOT NULL,
    comuna TEXT,
    region TEXT,
    pais TEXT NOT NULL,
    latitud REAL,
    longitud REAL
);
