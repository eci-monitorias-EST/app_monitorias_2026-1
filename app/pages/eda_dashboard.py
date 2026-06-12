"""Dashboard exploratorio interactivo (EDA) del flujo secuencial.

Reconstruye los 14 gráficos del EDA (6 de Aprobación de crédito y 8 de
Probabilidad de mora) como visualizaciones Plotly interactivas, organizadas
de lo macro (la tabla completa) a lo micro (cada variable y su relación con
el riesgo). Solo presentación: recibe un ``DatasetBundle`` ya cargado por los
servicios y no persiste estado.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from domain.models import ExerciseOption
from services.modeling import DatasetBundle

# ---------------------------------------------------------------------------
# Paleta Bankify
# ---------------------------------------------------------------------------
NAVY = "#08245c"
BLUE = "#155eef"
SKY = "#60a5fa"
GOOD = "#0ea472"
BAD = "#e11d48"
AMBER = "#f59e0b"
SLATE = "#334155"
GRID = "rgba(148, 163, 184, 0.28)"

TOTAL_CHARTS_APP = 14

# Diccionario de códigos del German Credit (statlog) a etiquetas legibles.
GERMAN_CODE_LABELS: dict[str, dict[str, str]] = {
    "status_checking_account": {
        "A11": "Saldo < 0 DM",
        "A12": "Saldo 0–200 DM",
        "A13": "Saldo ≥ 200 DM",
        "A14": "Sin cuenta corriente",
    },
    "credit_history": {
        "A30": "Sin créditos / todo pagado",
        "A31": "Pagados en este banco",
        "A32": "Créditos al día",
        "A33": "Atrasos en el pasado",
        "A34": "Cuenta crítica",
    },
    "purpose": {
        "A40": "Carro nuevo",
        "A41": "Carro usado",
        "A42": "Muebles / equipo",
        "A43": "Radio / TV",
        "A44": "Electrodomésticos",
        "A45": "Reparaciones",
        "A46": "Educación",
        "A48": "Re-entrenamiento",
        "A49": "Negocios",
        "A410": "Otros",
    },
    "savings_account": {
        "A61": "< 100 DM",
        "A62": "100–500 DM",
        "A63": "500–1.000 DM",
        "A64": "≥ 1.000 DM",
        "A65": "Sin ahorro conocido",
    },
    "employment_since": {
        "A71": "Desempleado",
        "A72": "< 1 año",
        "A73": "1–4 años",
        "A74": "4–7 años",
        "A75": "≥ 7 años",
    },
    "personal_status_sex": {
        "A91": "Hombre div./sep.",
        "A92": "Mujer div./sep./casada",
        "A93": "Hombre soltero",
        "A94": "Hombre casado/viudo",
        "A95": "Mujer soltera",
    },
    "other_debtors": {
        "A101": "Sin codeudor",
        "A102": "Codeudor solidario",
        "A103": "Garante",
    },
    "property": {
        "A121": "Bienes raíces",
        "A122": "Ahorro programado / seguro",
        "A123": "Carro u otro activo",
        "A124": "Sin propiedad conocida",
    },
    "other_installment_plans": {
        "A141": "Banco",
        "A142": "Tiendas",
        "A143": "Ninguno",
    },
    "housing": {
        "A151": "Alquiler",
        "A152": "Vivienda propia",
        "A153": "Vivienda gratuita",
    },
    "job": {
        "A171": "No calificado (no residente)",
        "A172": "No calificado (residente)",
        "A173": "Calificado / oficial",
        "A174": "Directivo / independiente",
    },
    "telephone": {
        "A191": "Sin teléfono",
        "A192": "Con teléfono",
    },
    "foreign_worker": {
        "A201": "Extranjero",
        "A202": "Local",
    },
}

DEFAULT_CODE_LABELS: dict[str, dict[int, str]] = {
    "SEX": {1: "Hombre", 2: "Mujer"},
    "EDUCATION": {
        0: "Desconocido",
        1: "Posgrado",
        2: "Universidad",
        3: "Secundaria",
        4: "Otros",
        5: "Desconocido",
        6: "Desconocido",
    },
    "MARRIAGE": {0: "Otros", 1: "Casado/a", 2: "Soltero/a", 3: "Otros"},
}

GERMAN_NUMERIC_PANEL = [
    ("duration_month", "Duración (meses)"),
    ("credit_amount", "Monto del crédito"),
    ("age_years", "Edad (años)"),
    ("installment_rate", "Tasa de cuota"),
    ("present_residence_since", "Antig. residencia"),
    ("existing_credits_bank", "Créditos vigentes"),
]

GERMAN_CATEGORICAL_PANEL = [
    ("status_checking_account", "Cuenta corriente"),
    ("credit_history", "Historial crediticio"),
    ("purpose", "Propósito del crédito"),
    ("savings_account", "Ahorros / bonos"),
    ("personal_status_sex", "Estado personal y sexo"),
    ("housing", "Vivienda"),
]

GERMAN_CORR_LABELS = {
    "duration_month": "Duración",
    "credit_amount": "Monto",
    "installment_rate": "Tasa cuota",
    "present_residence_since": "Antig. resid.",
    "age_years": "Edad",
    "existing_credits_bank": "Créd. vigentes",
    "liable_people": "Dependientes",
    "riesgo": "Riesgo (malo=1)",
}

DEFAULT_MATRIX_COLUMNS = (
    ["LIMIT_BAL", "AGE"]
    + [f"BILL_AMT{i}" for i in range(1, 7)]
    + [f"PAY_AMT{i}" for i in range(1, 7)]
    + ["Default"]
)

_PAY_STATUS_HINT = {
    -2: "Sin consumo",
    -1: "Pagó a tiempo",
    0: "Pago mínimo",
}


# ---------------------------------------------------------------------------
# Estilos del dashboard (solo este módulo)
# ---------------------------------------------------------------------------
_DASHBOARD_CSS = """
<style>
.eda-dash-hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(115deg, #061b52 0%, #0d3a8f 55%, #155eef 100%);
    border-radius: 14px;
    color: #ffffff;
    padding: 1.9rem 2.2rem 1.7rem;
    margin: 0.4rem 0 1.25rem;
    box-shadow: 0 18px 44px rgba(8, 36, 92, 0.22);
}
.eda-dash-hero::after {
    content: "";
    position: absolute;
    inset: 0 0 0 auto;
    width: 42%;
    background:
        radial-gradient(circle at 78% 22%, rgba(96, 165, 250, 0.35), transparent 55%),
        repeating-linear-gradient(115deg, transparent 0 16px, rgba(96, 165, 250, 0.12) 16px 17px);
}
.eda-dash-hero > * { position: relative; z-index: 1; }
.eda-dash-kicker {
    color: #93c5fd;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    margin: 0 0 0.4rem;
    text-transform: uppercase;
}
.eda-dash-hero h1 {
    font-size: 1.75rem;
    letter-spacing: 0;
    line-height: 1.15;
    margin: 0 0 0.65rem;
}
.eda-dash-hero p {
    color: rgba(219, 234, 254, 0.85);
    line-height: 1.55;
    margin: 0 0 1rem;
    max-width: 640px;
}
.eda-hero-pill {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.26);
    border-radius: 999px;
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 700;
    margin: 0 0.4rem 0.35rem 0;
    padding: 0.32rem 0.8rem;
}
.eda-questions-grid {
    display: grid;
    gap: 0.85rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: 0.5rem;
}
@media (max-width: 1100px) {
    .eda-questions-grid { grid-template-columns: 1fr; }
}
.eda-question-card {
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 12px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.07);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.eda-question-card header {
    align-items: center;
    display: flex;
    gap: 0.6rem;
    padding: 0.8rem 1rem 0.65rem;
}
.eda-q-num {
    align-items: center;
    border-radius: 10px;
    color: #ffffff;
    display: inline-flex;
    font-size: 0.95rem;
    font-weight: 900;
    height: 2rem;
    justify-content: center;
    min-width: 2rem;
}
.eda-question-card.macro .eda-q-num { background: #155eef; }
.eda-question-card.meso .eda-q-num { background: #0ea472; }
.eda-question-card.micro .eda-q-num { background: #e11d48; }
.eda-q-level {
    border-radius: 4px;
    font-size: 0.66rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    padding: 0.22rem 0.5rem;
    text-transform: uppercase;
}
.eda-question-card.macro .eda-q-level { background: #dbeafe; color: #1d4ed8; }
.eda-question-card.meso .eda-q-level { background: #d1fae5; color: #047857; }
.eda-question-card.micro .eda-q-level { background: #ffe4e6; color: #be123c; }
.eda-question-card p {
    color: #334155;
    flex: 1;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0;
    padding: 0 1rem 0.75rem;
}
.eda-question-card footer {
    background: #f8fafc;
    border-top: 1px solid #eef2f7;
    color: #64748b;
    font-size: 0.74rem;
    font-weight: 700;
    padding: 0.5rem 1rem;
}
.eda-kpi-row {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    margin: 0.25rem 0 1rem;
}
@media (max-width: 1100px) {
    .eda-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.eda-kpi-card {
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 12px;
    border-top: 3px solid var(--kpi-accent, #155eef);
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    padding: 0.85rem 1rem 0.9rem;
}
.eda-kpi-icon { font-size: 1.05rem; }
.eda-kpi-value {
    color: #0f172a;
    font-size: 1.55rem;
    font-weight: 900;
    line-height: 1.1;
    margin: 0.3rem 0 0.15rem;
}
.eda-kpi-label {
    color: #64748b;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.eda-level-banner {
    background: linear-gradient(90deg, rgba(21, 94, 239, 0.08), rgba(21, 94, 239, 0));
    border-left: 4px solid #155eef;
    border-radius: 6px;
    margin: 0.6rem 0 0.9rem;
    padding: 0.7rem 1rem;
}
.eda-level-banner.meso { border-left-color: #0ea472; background: linear-gradient(90deg, rgba(14, 164, 114, 0.09), rgba(14, 164, 114, 0)); }
.eda-level-banner.micro { border-left-color: #e11d48; background: linear-gradient(90deg, rgba(225, 29, 72, 0.08), rgba(225, 29, 72, 0)); }
.eda-level-banner h3 {
    color: #0f172a;
    font-size: 1.05rem;
    letter-spacing: 0;
    margin: 0 0 0.2rem;
}
.eda-level-banner p {
    color: #475569;
    font-size: 0.86rem;
    line-height: 1.45;
    margin: 0;
}
.eda-chart-head {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin: 1.1rem 0 0.2rem;
}
.eda-chart-num {
    background: #08245c;
    border-radius: 999px;
    color: #ffffff;
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 0.06em;
    padding: 0.26rem 0.7rem;
}
.eda-chart-tag {
    border-radius: 4px;
    font-size: 0.66rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    padding: 0.24rem 0.55rem;
    text-transform: uppercase;
}
.eda-chart-tag.macro { background: #dbeafe; color: #1d4ed8; }
.eda-chart-tag.meso { background: #d1fae5; color: #047857; }
.eda-chart-tag.micro { background: #ffe4e6; color: #be123c; }
.eda-chart-head h4 {
    color: #0f172a;
    font-size: 1rem;
    letter-spacing: 0;
    margin: 0;
}
.eda-probe-banner {
    background: linear-gradient(115deg, #0f172a, #1e293b);
    border-radius: 12px;
    color: #e2e8f0;
    margin: 1.4rem 0 0.8rem;
    padding: 1rem 1.2rem;
}
.eda-probe-banner h3 {
    color: #ffffff;
    font-size: 1.02rem;
    letter-spacing: 0;
    margin: 0 0 0.25rem;
}
.eda-probe-banner p {
    color: #94a3b8;
    font-size: 0.85rem;
    margin: 0;
}
</style>
"""


def _inject_dashboard_styles() -> None:
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)


def _html(markup: str) -> None:
    """Renderiza HTML aplanado en una sola línea.

    Markdown interpreta como bloque de código cualquier línea con 4+ espacios
    de indentación, por lo que el HTML multilínea generado con f-strings se
    filtraría como texto crudo.
    """
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Utilidades visuales
# ---------------------------------------------------------------------------
def _style_figure(
    fig: go.Figure,
    *,
    height: int = 430,
    title: str | None = None,
    show_legend: bool = True,
) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans Pro, sans-serif", color=SLATE, size=13),
        height=height,
        margin=dict(l=12, r=12, t=58 if title else 30, b=12),
        showlegend=show_legend,
        hoverlabel=dict(bgcolor="#0f172a", font=dict(color="#f8fafc", size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    if title:
        fig.update_layout(
            title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=NAVY))
        )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def _chart_header(number: int, total: int, level: str, title: str) -> None:
    level_names = {"macro": "Macro", "meso": "Variables", "micro": "Micro"}
    _html(
        f"""
        <div class="eda-chart-head">
            <span class="eda-chart-num">Gráfico {number} de {total}</span>
            <span class="eda-chart-tag {level}">{level_names[level]}</span>
            <h4>{title}</h4>
        </div>
        """
    )


def _render_chart(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


def _level_banner(css_class: str, title: str, copy: str) -> None:
    _html(
        f"""
        <div class="eda-level-banner {css_class}">
            <h3>{title}</h3>
            <p>{copy}</p>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Encabezado, preguntas guía y KPIs
# ---------------------------------------------------------------------------
def _render_hero(bundle: DatasetBundle, charts_in_exercise: int) -> None:
    rows = len(bundle.df)
    _html(
        f"""
        <section class="eda-dash-hero">
            <p class="eda-dash-kicker">Bankify Analytics Lab · Exploración de datos</p>
            <h1>Dashboard exploratorio — {bundle.label}</h1>
            <p>
                Recorrido de lo macro a lo micro: primero el panorama general de la tabla,
                después la distribución de cada variable y, al final, cómo se relacionan
                con el riesgo. Usa las tres preguntas guía para construir tu hallazgo.
            </p>
            <div>
                <span class="eda-hero-pill">📦 {rows:,} registros reales</span>
                <span class="eda-hero-pill">🧬 {len(bundle.features)} variables</span>
                <span class="eda-hero-pill">📊 {charts_in_exercise} gráficos en este proceso · {TOTAL_CHARTS_APP} en el dashboard</span>
            </div>
        </section>
        """
    )


def _render_guiding_questions(chart_hints: tuple[str, str, str]) -> None:
    questions = [
        (
            "macro",
            "Nivel macro",
            "¿Cómo está compuesta la base de clientes de Bankify y qué tan equilibrada "
            "está la variable objetivo entre clientes cumplidos y clientes en riesgo?",
            chart_hints[0],
        ),
        (
            "meso",
            "Variables",
            "¿Cómo se distribuyen las variables que describen al cliente (montos, plazos, "
            "edad, cupos y perfiles) y cuáles presentan valores atípicos o categorías dominantes?",
            chart_hints[1],
        ),
        (
            "micro",
            "Nivel micro",
            "Al cruzar las variables con el resultado real, ¿qué relaciones y perfiles de "
            "cliente concentran el mayor riesgo y cuáles resultan casi irrelevantes?",
            chart_hints[2],
        ),
    ]
    cards = "".join(
        f"""
        <article class="eda-question-card {css}">
            <header>
                <span class="eda-q-num">{index}</span>
                <span class="eda-q-level">{level}</span>
            </header>
            <p>{text}</p>
            <footer>Se responde con: {hint}</footer>
        </article>
        """
        for index, (css, level, text, hint) in enumerate(questions, start=1)
    )
    _html(f"<div class='eda-questions-grid'>{cards}</div>")
    st.caption(
        "Estas **3 preguntas** son las únicas del dashboard y cubren, en conjunto, "
        f"los {TOTAL_CHARTS_APP} gráficos de la exploración (6 de Aprobación de crédito "
        "y 8 de Probabilidad de mora)."
    )


def _render_kpis(bundle: DatasetBundle, risk_rate: float, risk_label: str) -> None:
    df = bundle.df
    features = df[bundle.features]
    numeric_count = features.select_dtypes(include=["number"]).shape[1]
    categorical_count = len(bundle.features) - numeric_count
    missing = int(features.isna().sum().sum())
    kpis = [
        ("🗂️", f"{len(df):,}", "Registros", BLUE),
        ("🧬", f"{len(bundle.features)}", "Variables", NAVY),
        ("🔢", f"{numeric_count} · {categorical_count}", "Numéricas · Categóricas", GOOD),
        ("🕳️", f"{missing:,}", "Datos faltantes", AMBER),
        ("⚠️", f"{risk_rate:.1%}", risk_label, BAD),
    ]
    cards = "".join(
        f"""
        <div class="eda-kpi-card" style="--kpi-accent: {accent};">
            <span class="eda-kpi-icon">{icon}</span>
            <div class="eda-kpi-value">{value}</div>
            <div class="eda-kpi-label">{label}</div>
        </div>
        """
        for icon, value, label, accent in kpis
    )
    _html(f"<div class='eda-kpi-row'>{cards}</div>")


def _render_table_preview(df: pd.DataFrame, key_prefix: str) -> None:
    with st.expander("🔎 Ver la tabla en bruto y su resumen estadístico"):
        st.dataframe(df.head(10), use_container_width=True, key=f"{key_prefix}_head")
        numeric = df.select_dtypes(include=["number"])
        if not numeric.empty:
            st.markdown("**Resumen de las variables numéricas**")
            st.dataframe(
                numeric.describe().T.round(2),
                use_container_width=True,
                key=f"{key_prefix}_describe",
            )


# ---------------------------------------------------------------------------
# Constructores de figuras compartidas
# ---------------------------------------------------------------------------
def _target_overview_figure(
    labels: list[str],
    counts: list[int],
    colors: list[str],
    center_text: str,
    bar_title: str,
) -> go.Figure:
    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "domain"}]],
        column_widths=[0.58, 0.42],
        subplot_titles=(bar_title, "Proporción"),
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=counts,
            marker=dict(color=colors, line=dict(color="rgba(15,23,42,0.25)", width=1)),
            text=[f"{value:,}" for value in counts],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:,} clientes<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=counts,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
            textinfo="percent",
            textfont=dict(size=14, color="#ffffff"),
            hovertemplate="<b>%{label}</b><br>%{value:,} clientes (%{percent})<extra></extra>",
        ),
        row=1,
        col=2,
    )
    fig.add_annotation(
        text=center_text,
        x=0.815,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=15, color=NAVY, family="Source Sans Pro"),
    )
    fig.update_yaxes(title_text="Clientes", row=1, col=1)
    _style_figure(fig, height=400, show_legend=True)
    fig.update_annotations(font=dict(color=NAVY))
    return fig


def _histogram_grid_figure(
    df: pd.DataFrame, panel: list[tuple[str, str]], rows: int, cols: int
) -> go.Figure:
    titles = []
    for column, label in panel:
        titles.append(f"{label} · μ = {df[column].mean():,.1f}")
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, vertical_spacing=0.16)
    for index, (column, _label) in enumerate(panel):
        row, col = divmod(index, cols)
        fig.add_trace(
            go.Histogram(
                x=df[column],
                marker=dict(color="rgba(21, 94, 239, 0.65)", line=dict(color="#ffffff", width=0.6)),
                hovertemplate="Rango: %{x}<br>Frecuencia: %{y}<extra></extra>",
                showlegend=False,
            ),
            row=row + 1,
            col=col + 1,
        )
        fig.add_vline(
            x=float(df[column].mean()),
            line_dash="dash",
            line_color=AMBER,
            line_width=2,
            row=row + 1,
            col=col + 1,
        )
    _style_figure(fig, height=620, show_legend=False)
    fig.update_annotations(font=dict(size=12.5, color=NAVY))
    return fig


def _box_grid_figure(
    df: pd.DataFrame, panel: list[tuple[str, str]], rows: int, cols: int
) -> go.Figure:
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=[label for _column, label in panel],
        vertical_spacing=0.14,
    )
    for index, (column, label) in enumerate(panel):
        row, col = divmod(index, cols)
        fig.add_trace(
            go.Box(
                y=df[column],
                name=label,
                boxpoints="outliers",
                marker=dict(color=BLUE, size=3, opacity=0.55),
                line=dict(color=NAVY, width=1.6),
                fillcolor="rgba(96, 165, 250, 0.35)",
                hoverinfo="y",
                showlegend=False,
            ),
            row=row + 1,
            col=col + 1,
        )
    fig.update_xaxes(showticklabels=False)
    _style_figure(fig, height=620, show_legend=False)
    fig.update_annotations(font=dict(size=12.5, color=NAVY))
    return fig


def _categorical_grid_figure(df: pd.DataFrame, panel: list[tuple[str, str]]) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=[label for _column, label in panel],
        vertical_spacing=0.1,
        horizontal_spacing=0.16,
    )
    for index, (column, _label) in enumerate(panel):
        row, col = divmod(index, 2)
        mapping = GERMAN_CODE_LABELS.get(column, {})
        counts = df[column].astype(str).map(lambda code: mapping.get(code, code)).value_counts()
        counts = counts.sort_values(ascending=True)
        fig.add_trace(
            go.Bar(
                x=counts.values,
                y=counts.index,
                orientation="h",
                marker=dict(
                    color=counts.values,
                    colorscale=[(0.0, "#bfdbfe"), (1.0, BLUE)],
                    line=dict(color="rgba(15,23,42,0.18)", width=0.8),
                ),
                text=counts.values,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>%{x:,} solicitudes<extra></extra>",
                showlegend=False,
            ),
            row=row + 1,
            col=col + 1,
        )
    _style_figure(fig, height=900, show_legend=False)
    fig.update_annotations(font=dict(size=12.5, color=NAVY))
    fig.update_xaxes(showgrid=True)
    return fig


def _lower_triangle_heatmap(
    matrix: pd.DataFrame,
    *,
    colorscale: str,
    zmid: float | None = None,
    show_values: bool = True,
    value_format: str = ".2f",
) -> go.Figure:
    masked = matrix.where(
        pd.DataFrame(
            [[r >= c for c in range(matrix.shape[1])] for r in range(matrix.shape[0])],
            index=matrix.index,
            columns=matrix.columns,
        )
    )
    heatmap = go.Heatmap(
        z=masked.values,
        x=list(masked.columns),
        y=list(masked.index),
        colorscale=colorscale,
        zmid=zmid,
        hoverongaps=False,
        hovertemplate="%{y} × %{x}<br>Valor: %{z:.3f}<extra></extra>",
        colorbar=dict(thickness=14, outlinewidth=0),
    )
    if show_values:
        heatmap.update(texttemplate=f"%{{z:{value_format}}}", textfont=dict(size=9))
    fig = go.Figure(heatmap)
    fig.update_yaxes(autorange="reversed")
    _style_figure(fig, height=560, show_legend=False)
    return fig


# ---------------------------------------------------------------------------
# Lupa interactiva (drill-down micro por variable)
# ---------------------------------------------------------------------------
def _variable_probe(
    bundle: DatasetBundle,
    good_mask: pd.Series,
    good_label: str,
    bad_label: str,
    value_mapper: dict[str, dict] | None,
) -> None:
    _html(
        """
        <div class="eda-probe-banner">
            <h3>🔍 Lupa interactiva: profundiza en cualquier variable</h3>
            <p>
                Elige una variable de la tabla y compárala contra el resultado real.
                Es la herramienta para llevar la pregunta 3 hasta el detalle más fino.
            </p>
        </div>
        """
    )
    labels = {descriptor.key: descriptor.label for descriptor in bundle.descriptors}
    feature = st.selectbox(
        "Variable a examinar",
        options=bundle.features,
        format_func=lambda key: f"{labels.get(key, key)} ({key})" if key in labels else key,
        key=f"eda_probe_{bundle.exercise}",
    )
    series = bundle.df[feature]
    is_numeric = pd.api.types.is_numeric_dtype(series)
    title = labels.get(feature, feature)

    if is_numeric and series.nunique() > 12:
        fig = go.Figure()
        for mask, name, color in (
            (good_mask, good_label, GOOD),
            (~good_mask, bad_label, BAD),
        ):
            values = series[mask]
            fig.add_trace(
                go.Histogram(
                    x=values,
                    name=name,
                    histnorm="percent",
                    marker=dict(color=color),
                    opacity=0.55,
                    hovertemplate="Rango: %{x}<br>%{y:.1f}% del grupo<extra></extra>",
                )
            )
            fig.add_vline(
                x=float(values.mean()),
                line_dash="dash",
                line_color=color,
                line_width=2,
            )
        fig.update_layout(barmode="overlay")
        _style_figure(
            fig,
            height=420,
            title=f"{title}: distribución comparada (líneas punteadas = promedio de cada grupo)",
        )
        _render_chart(fig, key=f"eda_probe_chart_{bundle.exercise}")
        return

    mapping = (value_mapper or {}).get(feature, {})

    def _label_for(value) -> str:
        if value in mapping:
            return str(mapping[value])
        text = str(value)
        if text in {str(k) for k in mapping}:
            return str(mapping[[k for k in mapping if str(k) == text][0]])
        if feature.startswith("PAY_") and is_numeric:
            numeric_value = int(value)
            return _PAY_STATUS_HINT.get(numeric_value, f"Atraso {numeric_value} meses")
        return text

    grouped = pd.DataFrame({"categoria": series.map(_label_for), "riesgo": (~good_mask).astype(int)})
    stats = (
        grouped.groupby("categoria")["riesgo"]
        .agg(tasa="mean", clientes="count")
        .sort_values("tasa", ascending=True)
    )
    overall = float((~good_mask).mean())
    fig = go.Figure(
        go.Bar(
            x=stats["tasa"].values,
            y=stats.index,
            orientation="h",
            marker=dict(
                color=stats["tasa"].values,
                colorscale=[(0.0, "#fecdd3"), (1.0, BAD)],
                line=dict(color="rgba(15,23,42,0.18)", width=0.8),
            ),
            customdata=stats["clientes"].values,
            text=[f"{value:.1%}" for value in stats["tasa"].values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Tasa de riesgo: %{x:.1%}<br>Clientes: %{customdata:,}<extra></extra>",
            showlegend=False,
        )
    )
    fig.add_vline(
        x=overall,
        line_dash="dash",
        line_color=NAVY,
        line_width=2,
        annotation_text=f"Tasa global {overall:.1%}",
        annotation_font_color=NAVY,
    )
    fig.update_xaxes(tickformat=".0%")
    _style_figure(
        fig,
        height=max(380, 56 * len(stats) + 120),
        title=f"{title}: tasa de riesgo por categoría",
        show_legend=False,
    )
    _render_chart(fig, key=f"eda_probe_chart_{bundle.exercise}")


# ---------------------------------------------------------------------------
# Dashboard: Aprobación de crédito (German Credit) — 6 gráficos
# ---------------------------------------------------------------------------
def _render_german_dashboard(bundle: DatasetBundle) -> None:
    df = bundle.df
    total = 6
    good_mask = df["credit_outcome"] == 1
    bad_rate = float((~good_mask).mean())

    _render_kpis(bundle, bad_rate, "Créditos malos")

    macro_tab, meso_tab, micro_tab = st.tabs(
        [
            "🛰️ Nivel macro · La tabla",
            "📊 Nivel medio · Las variables",
            "🔬 Nivel micro · Riesgo y relaciones",
        ]
    )

    with macro_tab:
        _level_banner(
            "macro",
            "Panorama general del portafolio",
            "Antes de mirar variables una a una, entiende el conjunto: cuántas solicitudes "
            "hay y cómo se reparten entre créditos buenos y malos. Aquí se responde la pregunta 1.",
        )
        _chart_header(1, total, "macro", "Balance de la variable objetivo: créditos buenos vs. malos")
        fig = _target_overview_figure(
            labels=["Bueno (1)", "Malo (2)"],
            counts=[int(good_mask.sum()), int((~good_mask).sum())],
            colors=[GOOD, BAD],
            center_text=f"<b>{bad_rate:.0%}</b><br>riesgo",
            bar_title="Distribución de créditos",
        )
        _render_chart(fig, key="eda_german_chart_1")
        st.caption(
            "💡 7 de cada 10 créditos del histórico terminaron bien: la clase 'malo' es minoritaria "
            "pero no marginal, y todo análisis posterior debe leerse con ese desbalance en mente."
        )
        _render_table_preview(df, key_prefix="eda_german_preview")

    with meso_tab:
        _level_banner(
            "meso",
            "Cada variable bajo el microscopio",
            "Distribuciones, valores atípicos y categorías dominantes de las variables del "
            "solicitante. Aquí se responde la pregunta 2.",
        )
        _chart_header(2, total, "meso", "Distribución de las variables numéricas (μ = promedio)")
        _render_chart(
            _histogram_grid_figure(df, GERMAN_NUMERIC_PANEL, rows=2, cols=3),
            key="eda_german_chart_2",
        )
        st.caption(
            "💡 Monto y duración están sesgados a la derecha: la mayoría pide créditos cortos y "
            "pequeños, con una cola de operaciones grandes que arrastra el promedio."
        )

        _chart_header(3, total, "meso", "Cajas y valores atípicos de las numéricas")
        _render_chart(
            _box_grid_figure(df, GERMAN_NUMERIC_PANEL, rows=2, cols=3),
            key="eda_german_chart_3",
        )
        st.caption(
            "💡 Los puntos fuera de los bigotes son solicitudes atípicas (créditos muy largos, "
            "montos altos o clientes mayores) que conviene vigilar antes de modelar."
        )

        _chart_header(4, total, "meso", "Frecuencia de las variables categóricas clave")
        _render_chart(
            _categorical_grid_figure(df, GERMAN_CATEGORICAL_PANEL),
            key="eda_german_chart_4",
        )
        st.caption(
            "💡 Los códigos del dataset original se tradujeron a etiquetas legibles: domina el "
            "solicitante sin cuenta corriente, con créditos al día, vivienda propia y poco ahorro."
        )

    with micro_tab:
        _level_banner(
            "micro",
            "Las variables frente al resultado del crédito",
            "Cruces directos contra la variable objetivo y relaciones entre variables. "
            "Aquí se responde la pregunta 3.",
        )
        _chart_header(5, total, "micro", "Duración y monto según el resultado del crédito")
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Duración del crédito (meses)", "Monto del crédito"),
        )
        for col_index, column in enumerate(("duration_month", "credit_amount"), start=1):
            for mask, name, color in ((good_mask, "Bueno", GOOD), (~good_mask, "Malo", BAD)):
                fig.add_trace(
                    go.Box(
                        y=df.loc[mask, column],
                        name=name,
                        legendgroup=name,
                        showlegend=col_index == 1,
                        boxpoints="outliers",
                        marker=dict(color=color, size=3, opacity=0.5),
                        line=dict(color=color, width=1.8),
                        fillcolor="rgba(255,255,255,0)",
                    ),
                    row=1,
                    col=col_index,
                )
        _style_figure(fig, height=460)
        fig.update_annotations(font=dict(size=13, color=NAVY))
        _render_chart(fig, key="eda_german_chart_5")
        st.caption(
            "💡 Los créditos malos tienden a ser más largos y de mayor monto: la mediana de "
            "duración del grupo 'malo' supera con claridad a la del grupo 'bueno'."
        )

        _chart_header(6, total, "micro", "Matriz de correlación (numéricas + riesgo)")
        numeric_columns = [column for column, _label in GERMAN_NUMERIC_PANEL] + ["liable_people"]
        corr_df = df[numeric_columns].copy()
        corr_df["riesgo"] = (~good_mask).astype(int)
        corr = corr_df.corr().rename(index=GERMAN_CORR_LABELS, columns=GERMAN_CORR_LABELS)
        fig = _lower_triangle_heatmap(corr, colorscale="RdBu_r", zmid=0.0)
        _render_chart(fig, key="eda_german_chart_6")
        st.caption(
            "💡 Duración y monto van de la mano (0.62) y son las numéricas más asociadas al "
            "riesgo; la edad apenas roza una relación negativa y los dependientes no aportan señal."
        )

        _variable_probe(
            bundle,
            good_mask=good_mask,
            good_label="Bueno",
            bad_label="Malo",
            value_mapper=GERMAN_CODE_LABELS,
        )


# ---------------------------------------------------------------------------
# Dashboard: Probabilidad de mora (Default Clientes) — 8 gráficos
# ---------------------------------------------------------------------------
def _render_default_dashboard(bundle: DatasetBundle) -> None:
    df = bundle.df
    total = 8
    good_mask = df["Default"] == 0
    default_rate = float((~good_mask).mean())

    _render_kpis(bundle, default_rate, "Tasa de impago")

    macro_tab, meso_tab, micro_tab = st.tabs(
        [
            "🛰️ Nivel macro · La tabla",
            "📊 Nivel medio · Las variables",
            "🔬 Nivel micro · Riesgo y relaciones",
        ]
    )

    with macro_tab:
        _level_banner(
            "macro",
            "Panorama general de la cartera",
            "Una mirada a los 30.000 clientes de tarjetas de crédito antes de entrar al "
            "detalle: cuántos cayeron en impago. Aquí se responde la pregunta 1.",
        )
        _chart_header(1, total, "macro", "Clientes por estado de impago (0 = al día, 1 = default)")
        fig = _target_overview_figure(
            labels=["Al día (0)", "En mora (1)"],
            counts=[int(good_mask.sum()), int((~good_mask).sum())],
            colors=[GOOD, BAD],
            center_text=f"<b>{default_rate:.1%}</b><br>en mora",
            bar_title="Cantidad de clientes",
        )
        _render_chart(fig, key="eda_default_chart_1")
        st.caption(
            "💡 Solo 1 de cada 5 clientes cayó en impago: el desbalance de clases obliga a "
            "evaluar los modelos con métricas que no premien predecir siempre 'al día'."
        )
        st.caption(
            "ℹ️ En esta tabla las variables demográficas (sexo, educación, estado civil) y los "
            "estados de pago vienen codificados como enteros: el conteo de numéricas los incluye."
        )
        _render_table_preview(df, key_prefix="eda_default_preview")

    with meso_tab:
        _level_banner(
            "meso",
            "El cupo de crédito bajo el microscopio",
            "La variable financiera central de esta tabla es el límite de crédito asignado "
            "(LIMIT_BAL). Aquí se responde la pregunta 2.",
        )
        _chart_header(2, total, "meso", "Distribución del límite de crédito (LIMIT_BAL)")
        fig = go.Figure(
            go.Histogram(
                x=df["LIMIT_BAL"],
                nbinsx=40,
                marker=dict(color="rgba(21, 94, 239, 0.65)", line=dict(color="#ffffff", width=0.6)),
                hovertemplate="Cupo: %{x}<br>Clientes: %{y:,}<extra></extra>",
            )
        )
        mean_limit = float(df["LIMIT_BAL"].mean())
        median_limit = float(df["LIMIT_BAL"].median())
        fig.add_vline(
            x=mean_limit,
            line_dash="dash",
            line_color=AMBER,
            line_width=2,
            annotation_text=f"Media {mean_limit:,.0f}",
            annotation_font_color=AMBER,
        )
        fig.add_vline(
            x=median_limit,
            line_dash="dot",
            line_color=NAVY,
            line_width=2,
            annotation_text=f"Mediana {median_limit:,.0f}",
            annotation_font_color=NAVY,
            annotation_position="bottom right",
        )
        fig.update_xaxes(title_text="Límite de crédito (NT$)")
        fig.update_yaxes(title_text="Frecuencia")
        _style_figure(fig, height=430, show_legend=False)
        _render_chart(fig, key="eda_default_chart_2")
        st.caption(
            "💡 La distribución es asimétrica: la mitad de la cartera tiene cupos bajos "
            "(mediana muy por debajo de la media) y una cola larga concentra los cupos altos."
        )

    with micro_tab:
        _level_banner(
            "micro",
            "Cupo, edad y comportamiento de pago frente a la mora",
            "Cruces de las variables contra el impago real y estructura de relaciones entre "
            "facturas y pagos. Aquí se responde la pregunta 3.",
        )

        _chart_header(3, total, "micro", "Límite de crédito según estado de impago")
        fig = go.Figure()
        for mask, name, color in ((good_mask, "Al día", GOOD), (~good_mask, "En mora", BAD)):
            fig.add_trace(
                go.Box(
                    y=df.loc[mask, "LIMIT_BAL"],
                    name=name,
                    boxpoints="outliers",
                    marker=dict(color=color, size=3, opacity=0.4),
                    line=dict(color=color, width=1.8),
                    fillcolor="rgba(255,255,255,0)",
                )
            )
        fig.update_yaxes(title_text="Límite de crédito (NT$)")
        _style_figure(fig, height=440)
        _render_chart(fig, key="eda_default_chart_3")
        st.caption(
            "💡 Los clientes en mora tienen cupos sistemáticamente menores: la mediana del grupo "
            "en default está muy por debajo, señal de que el banco ya los percibía como riesgosos."
        )

        _chart_header(4, total, "micro", "Proporción de impagos por rango de edad")
        age_bins = list(range(20, 85, 5))
        age_labels = [f"{start}-{start + 4}" for start in age_bins[:-1]]
        binned = pd.cut(df["AGE"], bins=age_bins, labels=age_labels, right=False)
        proportions = (
            pd.crosstab(binned, df["Default"], normalize="index")
            .reindex(age_labels)
            .dropna(how="all")
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=proportions.index.astype(str),
                y=proportions[1],
                name="En mora",
                marker=dict(color=BAD),
                hovertemplate="<b>%{x} años</b><br>En mora: %{y:.1%}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Bar(
                x=proportions.index.astype(str),
                y=proportions[0],
                name="Al día",
                marker=dict(color="rgba(14, 164, 114, 0.55)"),
                hovertemplate="<b>%{x} años</b><br>Al día: %{y:.1%}<extra></extra>",
            )
        )
        fig.add_hline(
            y=default_rate,
            line_dash="dash",
            line_color=NAVY,
            line_width=2,
            annotation_text=f"Tasa global {default_rate:.1%}",
            annotation_font_color=NAVY,
        )
        fig.update_layout(barmode="stack")
        fig.update_yaxes(tickformat=".0%", title_text="Proporción de clientes")
        fig.update_xaxes(title_text="Rango de edad (años)")
        _style_figure(fig, height=440)
        _render_chart(fig, key="eda_default_chart_4")
        st.caption(
            "💡 El riesgo no crece de forma lineal con la edad: los extremos (muy jóvenes y "
            "mayores de 60) superan la tasa global, mientras el tramo 30-40 es el más cumplido."
        )

        _chart_header(5, total, "micro", "Cupo promedio asignado según edad y comportamiento real")
        decade_bins = list(range(20, 90, 10))
        decade_labels = [f"{start}-{start + 9}" for start in decade_bins[:-1]]
        decades = pd.cut(df["AGE"], bins=decade_bins, labels=decade_labels, right=False)
        averages = (
            df.assign(decada=decades)
            .groupby(["decada", "Default"], observed=True)["LIMIT_BAL"]
            .mean()
            .unstack()
            .reindex(decade_labels)
            .dropna(how="all")
        )
        fig = go.Figure()
        for outcome, name, color in ((0, "Cumplió con el pago", GOOD), (1, "Cayó en impago", BAD)):
            fig.add_trace(
                go.Bar(
                    x=averages.index.astype(str),
                    y=averages[outcome],
                    name=name,
                    marker=dict(color=color),
                    text=[f"{value:,.0f}" for value in averages[outcome]],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="<b>%{x} años</b><br>Cupo promedio: %{y:,.0f} NT$<extra></extra>",
                )
            )
        fig.update_layout(barmode="group")
        fig.update_yaxes(title_text="Cupo promedio asignado (NT$)")
        fig.update_xaxes(title_text="Rango de edad (años)")
        _style_figure(fig, height=470)
        _render_chart(fig, key="eda_default_chart_5")
        st.caption(
            "💡 En casi todas las edades, quienes cayeron en mora tenían cupos promedio menores; "
            "la brecha se cierra en los mayores de 60, donde el cupo deja de diferenciar el riesgo."
        )

        _chart_header(6, total, "micro", "Matriz de covarianzas (triangular inferior)")
        covariance = df[DEFAULT_MATRIX_COLUMNS].cov()
        fig = _lower_triangle_heatmap(
            covariance, colorscale="Viridis", show_values=False
        )
        _render_chart(fig, key="eda_default_chart_6")
        st.caption(
            "💡 La covarianza está dominada por la escala de las facturas (BILL_AMT): valores "
            "enormes entre meses consecutivos. Por eso conviene pasar a la correlación de Spearman."
        )

        _chart_header(7, total, "micro", "Correlación de Spearman (triangular inferior)")
        spearman = df[DEFAULT_MATRIX_COLUMNS].corr(method="spearman")
        fig = _lower_triangle_heatmap(spearman, colorscale="RdBu_r", zmid=0.0)
        _render_chart(fig, key="eda_default_chart_7")
        st.caption(
            "💡 Las facturas mensuales son casi redundantes entre sí (ρ > 0.8); frente al default, "
            "las señales más fuertes son negativas: a mayor cupo y mayores pagos, menor mora."
        )

        _chart_header(8, total, "micro", "Pairplot de variables clave vs. estado de impago")
        sample = df.sample(n=min(2500, len(df)), random_state=42).assign(
            Estado=lambda frame: frame["Default"].map({0: "Al día", 1: "En mora"})
        )
        fig = px.scatter_matrix(
            sample,
            dimensions=["AGE", "LIMIT_BAL", "BILL_AMT1", "PAY_AMT1"],
            color="Estado",
            color_discrete_map={"Al día": GOOD, "En mora": BAD},
            opacity=0.4,
        )
        fig.update_traces(diagonal_visible=False, marker=dict(size=3.5))
        _style_figure(fig, height=640)
        _render_chart(fig, key="eda_default_chart_8")
        st.caption(
            "💡 Muestra aleatoria de 2.500 clientes: los casos en mora se concentran en cupos y "
            "pagos bajos, sin un patrón claro por edad. No hay fronteras limpias: el riesgo es "
            "multivariado."
        )

        _variable_probe(
            bundle,
            good_mask=good_mask,
            good_label="Al día",
            bad_label="En mora",
            value_mapper=DEFAULT_CODE_LABELS,
        )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def render_eda_dashboard(bundle: DatasetBundle) -> None:
    """Renderiza el dashboard exploratorio completo para el ejercicio activo."""
    _inject_dashboard_styles()
    if bundle.exercise == ExerciseOption.CREDIT_APPROVAL:
        charts_in_exercise = 6
        hints = ("Gráfico 1", "Gráficos 2 a 4", "Gráficos 5 y 6 + lupa interactiva")
    else:
        charts_in_exercise = 8
        hints = ("Gráfico 1", "Gráfico 2", "Gráficos 3 a 8 + lupa interactiva")

    _render_hero(bundle, charts_in_exercise)
    _render_guiding_questions(hints)

    if bundle.exercise == ExerciseOption.CREDIT_APPROVAL:
        _render_german_dashboard(bundle)
    else:
        _render_default_dashboard(bundle)
