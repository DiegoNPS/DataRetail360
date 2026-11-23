# Dashboard EP5 — DataRetail 360

Este artefacto implementa el encargo práctico, sin informe ni presentación.

## Ejecutar

1. Ejecutar `PREPARAR_ENTORNO.cmd` si el entorno no existe.
2. Ejecutar `EJECUTAR_COMPLETO.cmd` para construir la base Gold.
3. Ejecutar `EJECUTAR_DASHBOARD.cmd` y abrir la URL local indicada.

Alternativa desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

## Decisiones de diseño

- Audiencia: gerencia comercial y jefatura de operaciones.
- Jerarquía: filtros y tarjetas KPI, tendencias/comparaciones, relato y detalle.
- Filtros: período, región, canal y categoría.
- Drill-down: región → sucursal → producto crítico.
- Accesibilidad: navy, teal, azul, naranja, dorado y gris; texto junto a estados;
  sin pares rojo-verde ni codificación exclusivamente cromática.
- Inventario: medida semi-aditiva. Los totales actuales se calculan únicamente
  para el último snapshot; la serie diaria compara snapshots sin sumarlos.
- Historia: situación, complicación y decisión sugerida, sin afirmar causalidad.

## KPI

Las cinco fichas se encuentran en `dashboard/kpis.py` y se muestran dentro de la
aplicación. Cada una documenta nombre, objetivo, fórmula, fuente, unidad, meta,
alerta, dueño, frecuencia, clasificación y utilidad. Los umbrales son reglas del
caso académico y requieren aprobación del responsable antes de producción.

## Consulta en lenguaje natural

El modo predeterminado contiene cuatro preguntas curadas. El resultado se compara
con una consulta de referencia para detectar discrepancias. El modo opcional con
OpenAI genera una salida estructurada (`sql`, explicación y supuestos), pero el
programa aplica además controles propios:

- una sola sentencia `SELECT` o `WITH`;
- rechazo de operaciones de escritura y administración;
- lista cerrada de vistas Gold;
- conexión SQLite `mode=ro` y `PRAGMA query_only=ON`;
- máximo de 200 filas en pantalla;
- aviso explícito de que una validación estructural no valida el significado.

Para activar el modo generativo, defina `OPENAI_API_KEY`. Opcionalmente puede
definir `OPENAI_MODEL`; el valor predeterminado es `gpt-6-luna`. Sin clave, la
demostración curada permanece completamente funcional y reproducible.

## Correspondencia con la pauta

| Criterio | Evidencia |
|---|---|
| KPI documentados | pestaña **Fichas KPI** y `dashboard/kpis.py` |
| Wireframe y principios visuales | `docs/WIREFRAME_EP5.svg` y aplicación |
| Dashboard funcional | `dashboard/app.py` conectado a SQLite Gold |
| Storytelling | bloque situación–complicación–decisión del resumen |
| IA generativa y validación | pestaña **Consulta con IA**, `dashboard/nlq.py` y pruebas |
