-- Trazabilidad de la ejecución y de las fuentes procesadas.

CREATE TABLE etl_ejecuciones (
    id_ejecucion TEXT PRIMARY KEY,
    modo TEXT NOT NULL,
    estrategia TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT NOT NULL,
    estado TEXT NOT NULL
);

CREATE TABLE etl_rechazos (
    fuente TEXT NOT NULL,
    fila_origen INTEGER NOT NULL,
    clave_origen TEXT,
    motivo TEXT NOT NULL,
    id_ejecucion TEXT NOT NULL,
    registro_original TEXT NOT NULL
);

CREATE TABLE etl_duplicados (
    fuente TEXT NOT NULL,
    fila_origen INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    id_ejecucion TEXT NOT NULL
);

CREATE TABLE etl_conciliacion (
    fuente TEXT PRIMARY KEY,
    filas_leidas INTEGER NOT NULL,
    filas_aceptadas INTEGER NOT NULL,
    filas_rechazadas INTEGER NOT NULL,
    filas_duplicadas INTEGER NOT NULL,
    diferencia INTEGER NOT NULL CHECK(diferencia=0)
);

CREATE TABLE etl_cambios_producto (
    codigo_producto TEXT NOT NULL,
    tipo_scd INTEGER NOT NULL,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    fecha_efectiva TEXT NOT NULL
);

CREATE TABLE etl_fuentes (
    archivo TEXT PRIMARY KEY,
    filas INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    id_ejecucion TEXT NOT NULL
);
