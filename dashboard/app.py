"""Aplicación Streamlit para la evaluación EP5."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dashboard.datos import (  # noqa: E402
    detalle_stock_critico, fecha_stock_mas_reciente, limites_y_filtros,
    quiebres_por_sucursal, resumen_stock, resumen_ventas, serie_mensual,
    tendencia_quiebres, ventas_por_categoria,
)
from dashboard.kpis import catalogo_como_filas  # noqa: E402
from dashboard.nlq import (  # noqa: E402
    CONSULTAS_CURADAS, ejecutar_curada, ejecutar_sql_seguro, generar_sql,
)

NAVY, TEAL, BLUE, ORANGE, GOLD, GRAY = (
    "#0F2C4C", "#0E8C84", "#1F77B4", "#FF7F0E", "#C8860D", "#9AA7B2"
)

st.set_page_config(page_title="DataRetail 360", page_icon="📊", layout="wide")
st.markdown("""
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {background:#F5F7F9; border-left:5px solid #0E8C84;
        padding:0.8rem 1rem; border-radius:0.45rem; min-height:132px;}
    [data-testid="stMetricLabel"] {font-weight:700; color:#0F2C4C;}
    [data-testid="stMetricValue"] {color:#0F2C4C !important;}
    [data-testid="stMetricDelta"] {color:#52606D !important;}
    [data-testid="stMetricDelta"] svg {display:none;}
    h1,h2,h3 {color:#0F2C4C;}
    .story {background:#EDF6F5; border-left:5px solid #0E8C84; padding:1rem 1.2rem;
        border-radius:0.4rem; color:#0F2C4C;}
    .small-note {color:#52606D; font-size:0.88rem;}
    @media (max-width: 900px) {
        [data-testid="stHorizontalBlock"] {flex-wrap:wrap !important; gap:0.75rem;}
        [data-testid="stColumn"], [data-testid="column"] {
            min-width:240px !important; flex:1 1 240px !important; width:auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def pesos(valor):
    return f"${valor/1_000_000_000:,.1f} mil MM".replace(",", "X").replace(".", ",").replace("X", ".")


def porcentaje(valor):
    return "Sin base comparable" if valor is None else f"{valor:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def estilo_figura(fig, titulo, eje_y=None):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color=NAVY)),
        colorway=[TEAL, BLUE, ORANGE, GOLD, GRAY], template="plotly_white",
        margin=dict(l=20, r=20, t=65, b=25), hoverlabel=dict(namelength=-1),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, title_text="")
    fig.update_yaxes(gridcolor="#E6EAED", rangemode="tozero", title_text=eje_y or "")
    return fig


st.title("DataRetail 360 · Ventas e inventario")
st.caption("Panel ejecutivo para decisiones comerciales y de reposición · modelo dimensional Gold")

try:
    opciones = limites_y_filtros()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.header("Filtros")
    inicio_predeterminado = date(opciones["fecha_max"].year, 1, 1)
    rango = st.date_input(
        "Período de ventas", (max(opciones["fecha_min"], inicio_predeterminado), opciones["fecha_max"]),
        min_value=opciones["fecha_min"], max_value=opciones["fecha_max"],
    )
    if not isinstance(rango, (tuple, list)) or len(rango) != 2:
        st.info("Seleccione una fecha inicial y una final.")
        st.stop()
    inicio, fin = rango
    regiones = st.multiselect("Región de sucursal", opciones["regiones"])
    canales = st.multiselect("Canal", opciones["canales"])
    categorias = st.multiselect("Categoría", opciones["categorias"])
    st.divider()
    st.caption("Los filtros vacíos incluyen todos los valores. El inventario siempre usa un único snapshot.")

resumen, stock = resumen_ventas(inicio, fin, regiones, canales, categorias), resumen_stock(
    regiones=regiones, categorias=categorias)
tabs = st.tabs(["Resumen ejecutivo", "Inventario", "Fichas KPI", "Consulta con IA"])

with tabs[0]:
    st.subheader("Indicadores clave")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Venta neta", pesos(resumen["venta_neta"]),
              porcentaje(resumen["crecimiento"]) + " interanual" if resumen["crecimiento"] is not None else None)
    c2.metric("Crecimiento interanual", porcentaje(resumen["crecimiento"]), "Meta: ≥ 0%")
    c3.metric("Tasa de devoluciones", porcentaje(resumen["tasa_devoluciones"]), "Meta: ≤ 2%", delta_color="inverse")
    c4.metric("Quiebre de stock", porcentaje(stock["tasa_quiebre"]), f"Cierre {stock['fecha']} · meta ≤ 5%", delta_color="inverse")
    c5.metric("Disponibilidad", porcentaje(stock["disponibilidad"]), "Meta: ≥ 90%")
    st.caption("▲/▼ expresa cambio o referencia; cada tarjeta incluye texto, no depende solo del color.")

    mensual = serie_mensual(inicio, fin, regiones, canales, categorias)
    categorias_df = ventas_por_categoria(inicio, fin, regiones, canales, categorias)
    izquierda, derecha = st.columns([1.65, 1])
    with izquierda:
        fig = px.line(mensual, x="mes", y="venta_neta", markers=True)
        fig.update_traces(line_color=TEAL, line_width=3, marker_size=7,
                          hovertemplate="%{x}<br>Venta neta: $%{y:,.0f}<extra></extra>")
        st.plotly_chart(estilo_figura(fig, "Evolución mensual de la venta neta", "CLP"), width="stretch")
    with derecha:
        fig = px.bar(categorias_df.sort_values("venta_neta"), x="venta_neta", y="categoria", orientation="h", text_auto=".3s")
        fig.update_traces(marker_color=BLUE, hovertemplate="%{y}<br>Venta neta: $%{x:,.0f}<extra></extra>")
        st.plotly_chart(estilo_figura(fig, "Venta neta por categoría", ""), width="stretch")

    crecimiento = resumen["crecimiento"]
    situacion = f"Entre {inicio} y {fin}, la venta neta alcanzó {pesos(resumen['venta_neta'])}."
    if crecimiento is None:
        complicacion = "No existe una base interanual completa para el período filtrado; la comparación requiere cautela."
    elif crecimiento >= 0:
        complicacion = f"El resultado supera en {porcentaje(crecimiento)} al período comparable, pero la tasa de devoluciones es {porcentaje(resumen['tasa_devoluciones'])}."
    else:
        complicacion = f"El resultado cae {porcentaje(abs(crecimiento))} frente al período comparable; conviene revisar región, canal y categoría."
    accion = (f"El cierre de inventario registra {porcentaje(stock['tasa_quiebre'])} de posiciones agotadas. "
              "Priorice las sucursales y productos críticos del detalle antes de definir reposición.")
    st.markdown(f"<div class='story'><b>Situación.</b> {situacion}<br><b>Complicación.</b> {complicacion}<br><b>Decisión sugerida.</b> {accion}</div>", unsafe_allow_html=True)
    st.caption("La recomendación identifica prioridades; no atribuye causalidad sin un análisis adicional.")

with tabs[1]:
    st.subheader(f"Inventario al {stock['fecha']}")
    a, b, c, d = st.columns(4)
    a.metric("Stock disponible", f"{stock['stock_disponible']:,.0f}".replace(",", "."), "unidades")
    b.metric("Valor del stock", pesos(stock["valor_stock"]), "último snapshot")
    c.metric("Quiebre", porcentaje(stock["tasa_quiebre"]), "Meta: ≤ 5%", delta_color="inverse")
    d.metric("Disponibilidad", porcentaje(stock["disponibilidad"]), "Meta: ≥ 90%")
    trend = tendencia_quiebres(regiones, categorias)
    tiendas = quiebres_por_sucursal(regiones=regiones, categorias=categorias)
    izq, der = st.columns([1.35, 1])
    with izq:
        fig = px.line(trend, x="fecha_stock", y="tasa_quiebre", markers=True)
        fig.add_hline(y=5, line_dash="dash", line_color=GOLD,
                      annotation_text="Meta ≤ 5%", annotation_position="top left")
        fig.update_traces(line_color=TEAL, hovertemplate="%{x}<br>Quiebre: %{y:.2f}%<extra></extra>")
        st.plotly_chart(estilo_figura(fig, "Quiebre diario: tendencia y meta", "% de posiciones"), width="stretch")
    with der:
        fig = px.bar(tiendas.sort_values("quiebres"), x="quiebres", y="nombre_sucursal", orientation="h")
        fig.update_traces(marker_color=ORANGE, hovertemplate="%{y}<br>Quiebres: %{x}<extra></extra>")
        st.plotly_chart(estilo_figura(fig, "Sucursales con más quiebres", ""), width="stretch")

    st.subheader("Drill-down: región → sucursal → producto")
    sucursales = ["Todas"] + tiendas["nombre_sucursal"].tolist()
    sucursal = st.selectbox("Sucursal a inspeccionar", sucursales)
    detalle = detalle_stock_critico(regiones=regiones, categorias=categorias,
                                    sucursal=None if sucursal == "Todas" else sucursal)
    st.dataframe(detalle, width="stretch", hide_index=True,
                 column_config={"stock_disponible": st.column_config.NumberColumn("Disponible"),
                                "estado_stock": st.column_config.TextColumn("Estado")})
    st.caption("Se muestran hasta 500 posiciones con 5 o menos unidades disponibles. AGOTADO y CRÍTICO aparecen como texto para no depender del color.")

with tabs[2]:
    st.subheader("Fichas de KPI")
    st.write("Definiciones operativas usadas en las tarjetas y sus criterios de gestión.")
    fichas = pd.DataFrame(catalogo_como_filas())
    st.dataframe(fichas, width="stretch", hide_index=True)
    st.info("Los umbrales son reglas de gestión del caso académico. Deben ser aprobados por los dueños del proceso antes de usarlos en producción.")

with tabs[3]:
    st.subheader("Consulta en lenguaje natural y validación")
    modo = st.radio("Modo", ["Preguntas curadas (verificable)", "Generación con OpenAI API"], horizontal=True)
    if modo.startswith("Preguntas"):
        pregunta = st.selectbox("Pregunta de negocio", list(CONSULTAS_CURADAS))
        if st.button("Ejecutar consulta validada", type="primary"):
            sql, resultado, validacion = ejecutar_curada(pregunta)
            st.code(sql.strip(), language="sql")
            (st.success if validacion.valido else st.error)(f"{validacion.nivel}: {' '.join(validacion.mensajes)}")
            st.dataframe(resultado, width="stretch", hide_index=True)
    else:
        st.caption("Requiere OPENAI_API_KEY. El modelo propone SQL; el programa lo valida y ejecuta en una conexión SQLite de solo lectura.")
        pregunta = st.text_input("Pregunta", placeholder="Ej.: ¿Qué regiones concentran más quiebres en el último cierre?")
        if st.button("Generar, validar y ejecutar", type="primary", disabled=not pregunta):
            try:
                propuesta = generar_sql(pregunta)
                st.write(propuesta.explicacion)
                st.code(propuesta.sql, language="sql")
                resultado, validacion = ejecutar_sql_seguro(propuesta.sql)
                (st.success if validacion.valido else st.error)(f"Validación {validacion.nivel}: {' '.join(validacion.mensajes)}")
                if propuesta.supuestos:
                    st.warning("Supuestos declarados: " + "; ".join(propuesta.supuestos))
                if validacion.valido:
                    st.dataframe(resultado, width="stretch", hide_index=True)
            except Exception as exc:
                st.error(f"No fue posible completar la consulta: {exc}")
        st.warning("Una consulta generada puede ser sintácticamente segura y aun interpretar mal el negocio. Revise SQL, grano, filtros y totales antes de decidir.")

st.divider()
st.caption("DataRetail 360 · fuente: SQLite Gold · actualización: última ejecución ETL disponible")
