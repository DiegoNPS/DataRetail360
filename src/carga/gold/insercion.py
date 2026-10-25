"""Mecanismo compartido para insertar DataFrames en tablas Gold existentes."""


def cargar_tablas(conexion, tablas, nombres):
    """Inserta DataFrames en tablas ya creadas y dentro de la transacción recibida."""
    for nombre in nombres:
        tablas[nombre].to_sql(nombre, conexion, if_exists='append', index=False, chunksize=2000)
