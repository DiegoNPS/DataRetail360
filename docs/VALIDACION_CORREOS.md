# Validación de correos: explicación para la presentación

Esta es una nueva versión de los datos sintéticos, identificada como `360-correos-v2` en el manifiesto. La actualización fue deliberada antes de ejecutar la ETL; la transformación no modifica Bronze ni recalcula su manifiesto para ocultar cambios.

## Datos y propósito

Los 10.000 clientes originales conservan su identidad, región, segmento y fechas. Sus direcciones ahora combinan Gmail, Hotmail, Outlook, example.com, example.org y ventas.example.com, con puntos, guiones bajos, números y etiquetas `+compras`. Las 100 copias originales conservan su equivalencia después de normalizar.

Se añadieron ocho clientes independientes, sin ventas ni cambios asociados: un correo vacío y siete mal formados. Sus errores son ausencia de arroba, doble arroba, punto inicial, puntos consecutivos, espacio interior, dominio con guion inicial y dominio sin extensión.

Las direcciones son generadas para estudio; no se envían mensajes. La existencia de Gmail o Hotmail no significa que el buzón generado esté comprobado. No se debe usar una lista de proveedores como criterio de validez.

## Transformación y decisión

1. Normalizar el correo con recorte de espacios externos y minúsculas, manteniendo la convención de identidad del proyecto.
2. Retirar copias idénticas normalizadas y auditar.
3. Detener ante IDs contradictorios, como antes.
4. Validar formato con `src/comun/correos.py`.
5. Rechazar y auditar `correo_vacio` o `correo_formato_invalido`, conservando registro original y fila CSV.
6. Mantener el control de unicidad entre correos aceptados y las demás validaciones del maestro.

El validador exige una arroba, parte local de 1 a 64 caracteres permitidos, longitud total máxima 254, ausencia de espacios, puntos locales sin extremos ni repeticiones, etiquetas de dominio de hasta 63 caracteres sin guiones en extremos y extensión alfabética de 2 a 63 letras. Admite subdominios. No implementa todas las variantes del RFC: direcciones entre comillas, dominios literales y correos internacionales Unicode quedan fuera del contrato académico.

No corrige automáticamente `gmal.com` a `gmail.com`: un dominio desconocido puede ser legítimo. Tampoco elimina puntos o etiquetas `+`, porque esas reglas dependen del proveedor.

## Eficiencia

La expresión y las comprobaciones se aplican una vez por cliente. El costo es lineal en el número y longitud de las direcciones y despreciable frente al procesamiento de ventas en este conjunto. No hay esperas de red, DNS o SMTP.

## Resultado esperado

10.108 filas = 10.000 aceptadas + 100 duplicadas + 8 rechazadas. Siguen existiendo 12.000 versiones SCD 2 y las mismas ventas, devoluciones e importes. El total de rechazos pasa de 16 a 24; los duplicados siguen en 727. Cambian la huella de clientes Bronze y el contenido/huella de dim_cliente, porque los correos ahora son distintos.

Si se introdujera un correo inválido en un cliente con cambios asociados, la carga se detendría por referencia maestra inválida. Si no tiene cambios pero sí ventas, estas se rechazarían por cliente desconocido. Es una política de calidad estricta que se debe explicar; estos ocho casos se aislaron para no alterar las métricas comerciales del ejercicio.

## Cómo explicarlo al profesor

“Separamos normalización de validación: quitar espacios y unificar mayúsculas resuelve representación; comprobar estructura identifica correos mal formados. Los registros inválidos no desaparecen silenciosamente: quedan en rechazos y conciliación. Admitimos cualquier dominio con estructura válida, y no confundimos sintaxis con existencia del buzón.”
