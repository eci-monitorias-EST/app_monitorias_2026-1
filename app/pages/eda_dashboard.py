"""Dashboard exploratorio (EDA) del flujo secuencial.

Presenta los 14 gráficos del EDA tal como fueron construidos en los
notebooks (6 de Aprobación de crédito y 8 de Probabilidad de mora,
servidos desde ``app/assets/eda``), organizados como un cuaderno de
analista que va de lo macro (la tabla completa) a lo micro (cada
variable frente al riesgo). Solo presentación: recibe un
``DatasetBundle`` ya cargado por los servicios y no persiste estado.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from domain.models import ExerciseOption
from services.modeling import DatasetBundle

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "eda"

TOTAL_FIGURES_APP = 14

# ---------------------------------------------------------------------------
# Inventario de figuras por ejercicio: (archivo, capítulo, título, nota al pie)
# Las notas están escritas en primera persona, como apuntes de quien hizo el EDA.
# ---------------------------------------------------------------------------
GERMAN_FIGURES = [
    (
        "german_credit_01.png",
        1,
        "Distribución de la variable objetivo",
        "700 créditos buenos contra 300 malos. Ese 30% de riesgo no es poca cosa "
        "para un banco; y como los malos son minoría, toca leer el resto del "
        "cuaderno con ese desbalance en la cabeza.",
    ),
    (
        "german_credit_02.png",
        2,
        "Histogramas de las variables numéricas",
        "Casi todo el mundo pide créditos cortos y pequeños: monto y duración se "
        "amontonan a la izquierda y dejan colas largas. Esas colas son las que "
        "después dan sustos.",
    ),
    (
        "german_credit_03.png",
        2,
        "Cajas y valores atípicos",
        "Los puntos sueltos por encima de los bigotes son las solicitudes raras: "
        "créditos de más de 60 meses, montos de cinco cifras y clientes de 70 "
        "años. Pocas, pero existen.",
    ),
    (
        "german_credit_04.png",
        2,
        "Frecuencia de las categóricas clave",
        "El perfil que domina sorprende: sin cuenta corriente (A14), con créditos "
        "al día (A32), ahorro mínimo (A61), hombre soltero (A93) y vivienda "
        "propia (A152). El diccionario del paso anterior ayuda a traducir los códigos.",
    ),
    (
        "german_credit_05.png",
        3,
        "Duración y monto según el resultado del crédito",
        "Aquí está la pista fuerte del capítulo: los créditos que salieron malos "
        "(grupo 2) eran más largos y más grandes desde el día uno. La mediana de "
        "duración del grupo malo queda claramente por encima.",
    ),
    (
        "german_credit_06.png",
        3,
        "Matriz de correlación",
        "Duración y monto van pegados (0.62), así que cuentan casi la misma "
        "historia. Contra el target nada pasa de 0.21: el riesgo no se explica "
        "con una sola variable, hay que cruzarlas.",
    ),
]

DEFAULT_FIGURES = [
    (
        "default_clients_01.png",
        1,
        "Clientes por estado de impago",
        "23.364 al día contra 6.636 en mora: 22,1%. Uno de cada cinco. Cualquier "
        "modelo que prediga siempre «al día» acierta el 78% de las veces sin "
        "aprender nada; ojo con eso al evaluar.",
    ),
    (
        "default_clients_02.png",
        2,
        "Distribución del límite de crédito",
        "El sesgo a la derecha es de manual: la mayoría de los cupos vive por "
        "debajo de NT$ 200.000 y una cola larga concentra los cupos grandes. La "
        "media queda inflada por esa cola.",
    ),
    (
        "default_clients_03.png",
        3,
        "Límite de crédito según estado de impago",
        "Quien cayó en mora tenía, de entrada, cupos más bajos: la caja del grupo "
        "1 está corrida hacia abajo. El banco ya los percibía como riesgosos "
        "antes de que dejaran de pagar.",
    ),
    (
        "default_clients_04.png",
        3,
        "Proporción de impagos por edad",
        "La tasa de mora ronda el 20–25% en casi todas las edades; no crece en "
        "línea recta. Los extremos (muy jóvenes y mayores de 60) son los que se "
        "salen del promedio.",
    ),
    (
        "default_clients_05.png",
        3,
        "Cupo promedio según edad y comportamiento real",
        "En cada rango de edad los cumplidos tenían más cupo que los morosos... "
        "hasta los 70–79, donde la brecha desaparece y el cupo deja de "
        "diferenciar el riesgo.",
    ),
    (
        "default_clients_06.png",
        3,
        "Matriz de covarianzas",
        "Está dominada por la escala de las facturas (BILL_AMT): números enormes "
        "entre meses consecutivos. La covarianza cruda engaña cuando las "
        "unidades son tan distintas; por eso la siguiente figura usa Spearman.",
    ),
    (
        "default_clients_07.png",
        3,
        "Correlación de Spearman",
        "Las facturas se copian de un mes a otro (ρ > 0.8): son casi redundantes. "
        "Frente al default lo que pesa va en negativo: a mayor cupo y mayores "
        "pagos, menos mora (−0.17 y −0.16).",
    ),
    (
        "default_clients_08.png",
        3,
        "Pairplot: variables clave vs. estado de impago",
        "No hay frontera limpia entre verdes y naranjas en ningún cruce: la mora "
        "no se separa con dos variables. El riesgo es multivariado, y eso "
        "justifica pasar a un modelo.",
    ),
]

CHAPTERS = {
    1: (
        "La tabla completa",
        "Antes de mirar variables una a una: cuántos registros hay, qué los "
        "describe y cómo se reparte la variable objetivo. Aquí vive la pregunta 1.",
    ),
    2: (
        "Variable por variable",
        "Distribuciones, atípicos y categorías dominantes. El microscopio sobre "
        "cada columna de la tabla. Aquí vive la pregunta 2.",
    ),
    3: (
        "Frente al riesgo",
        "Los cruces contra el resultado real y las relaciones entre variables. "
        "El terreno de la pregunta 3.",
    ),
}


# ---------------------------------------------------------------------------
# Estilos del cuaderno (solo este módulo)
# ---------------------------------------------------------------------------
_NOTEBOOK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=Caveat:wght@500;600&display=swap');

.nb-masthead {
    position: relative;
    background: #fffdf7;
    border: 1px solid #e2ddd0;
    border-top: 6px double #0f2c6b;
    border-radius: 3px;
    box-shadow: 0 14px 34px rgba(15, 44, 107, 0.10);
    margin: 0.4rem 0 1.6rem;
    padding: 1.7rem 2.1rem 1.5rem;
}
.nb-kicker {
    color: #8a8474;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    margin: 0 0 0.55rem;
    text-transform: uppercase;
}
.nb-masthead h1 {
    color: #101828;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2.15rem;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.08;
    margin: 0 0 0.55rem;
    max-width: 78%;
}
.nb-masthead h1 em {
    color: #0f2c6b;
    font-style: italic;
}
.nb-standfirst {
    color: #4b5563;
    font-size: 0.98rem;
    line-height: 1.6;
    margin: 0 0 1rem;
    max-width: 70%;
}
.nb-stamp {
    position: absolute;
    top: 1.6rem;
    right: 1.8rem;
    transform: rotate(5deg);
    border: 2.5px solid #b3402f;
    border-radius: 6px;
    color: #b3402f;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    line-height: 1.35;
    opacity: 0.82;
    padding: 0.45rem 0.7rem;
    text-align: center;
    text-transform: uppercase;
}
.nb-ficha {
    border-top: 1px dashed #d6d0bf;
    color: #6b7280;
    font-size: 0.85rem;
    padding-top: 0.75rem;
}
.nb-ficha strong { color: #101828; }

.nb-notas {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0.2rem 0 0.4rem;
}
@media (max-width: 1100px) { .nb-notas { grid-template-columns: 1fr; } }
.nb-nota {
    position: relative;
    border-radius: 2px;
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.13);
    min-height: 168px;
    padding: 1.35rem 1.1rem 0.95rem;
}
.nb-nota::before {
    content: "";
    position: absolute;
    top: -9px;
    left: 50%;
    width: 92px;
    height: 20px;
    transform: translateX(-50%) rotate(-2deg);
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(15, 23, 42, 0.08);
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.06);
}
.nb-nota.uno { background: #fff7c2; transform: rotate(-0.9deg); }
.nb-nota.dos { background: #defbe9; transform: rotate(0.6deg); }
.nb-nota.tres { background: #ffe8ec; transform: rotate(-0.4deg); }
.nb-nota-num {
    color: rgba(16, 24, 40, 0.35);
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.6rem;
    font-style: italic;
    font-weight: 700;
    line-height: 1;
}
.nb-nota p {
    color: #1f2937;
    font-size: 0.92rem;
    line-height: 1.5;
    margin: 0.45rem 0 0.6rem;
}
.nb-nota mark {
    background: transparent;
    box-shadow: inset 0 -0.55em rgba(255, 200, 50, 0.55);
    color: inherit;
    padding: 0;
}
.nb-nota.dos mark { box-shadow: inset 0 -0.55em rgba(52, 211, 153, 0.4); }
.nb-nota.tres mark { box-shadow: inset 0 -0.55em rgba(251, 113, 133, 0.35); }
.nb-nota-pista {
    color: #374151;
    display: block;
    font-family: 'Caveat', cursive;
    font-size: 1.12rem;
    line-height: 1.2;
}
.nb-notas-pie {
    color: #8a8474;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0.7rem 0 0.3rem;
    text-align: right;
}

.nb-capitulo {
    align-items: baseline;
    border-bottom: 1px solid #e2ddd0;
    display: flex;
    gap: 1.05rem;
    margin: 0.8rem 0 1.2rem;
    padding-bottom: 0.85rem;
}
.nb-cap-num {
    color: rgba(15, 44, 107, 0.22);
    font-family: 'Fraunces', Georgia, serif;
    font-size: 3rem;
    font-weight: 700;
    line-height: 0.9;
}
.nb-capitulo h3 {
    color: #101828;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.32rem;
    font-weight: 700;
    letter-spacing: 0;
    margin: 0 0 0.25rem;
}
.nb-capitulo p {
    color: #6b7280;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0;
    max-width: 660px;
}

.nb-ficha-tecnica {
    background: #fffdf7;
    border: 1px solid #e2ddd0;
    border-left: 4px solid #0f2c6b;
    border-radius: 3px;
    margin: 0 0 1.3rem;
    padding: 0.9rem 1.25rem 0.95rem;
}
.nb-ficha-tecnica h4 {
    color: #8a8474;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    margin: 0 0 0.55rem;
    text-transform: uppercase;
}
.nb-ficha-fila {
    border-bottom: 1px dotted #d6d0bf;
    color: #4b5563;
    display: flex;
    font-size: 0.9rem;
    justify-content: space-between;
    padding: 0.32rem 0;
}
.nb-ficha-fila:last-child { border-bottom: 0; }
.nb-ficha-fila strong { color: #101828; }

.nb-fig-head {
    align-items: baseline;
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin: 1.5rem 0 0.5rem;
}
.nb-fig-num {
    color: #0f2c6b;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 0.92rem;
    font-style: italic;
    font-weight: 700;
    letter-spacing: 0.04em;
    white-space: nowrap;
}
.nb-fig-head h4 {
    border-bottom: 2px solid rgba(15, 44, 107, 0.18);
    color: #101828;
    font-size: 1.02rem;
    letter-spacing: 0;
    margin: 0;
    padding-bottom: 0.15rem;
}
.nb-fig-nota {
    border-left: 3px solid rgba(179, 64, 47, 0.45);
    color: #243b6b;
    font-family: 'Caveat', cursive;
    font-size: 1.28rem;
    line-height: 1.3;
    margin: 0.45rem 0 0.4rem 0.3rem;
    max-width: 860px;
    padding: 0.1rem 0 0.1rem 0.85rem;
    transform: rotate(-0.25deg);
}

.nb-cierre {
    border-top: 1px solid #e2ddd0;
    color: #6b7280;
    font-size: 0.9rem;
    font-style: italic;
    margin-top: 1.6rem;
    padding-top: 0.9rem;
}
</style>
"""


def _inject_notebook_styles() -> None:
    st.markdown(_NOTEBOOK_CSS, unsafe_allow_html=True)


def _html(markup: str) -> None:
    """Renderiza HTML aplanado en una sola línea.

    Markdown interpreta como bloque de código cualquier línea con 4+ espacios
    de indentación, por lo que el HTML multilínea generado con f-strings se
    filtraría como texto crudo.
    """
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Piezas del cuaderno
# ---------------------------------------------------------------------------
def _render_masthead(bundle: DatasetBundle, figures_count: int, risk_rate: float) -> None:
    df = bundle.df
    risk_phrase = (
        f"{risk_rate:.0%} terminó mal"
        if bundle.exercise == ExerciseOption.CREDIT_APPROVAL
        else f"{risk_rate:.1%} cayó en mora"
    )
    _html(
        f"""
        <section class="nb-masthead">
            <p class="nb-kicker">Bankify · Ingeniería Estadística · Cuaderno de exploración</p>
            <h1>Lo que cuentan los datos de <em>{bundle.label.lower()}</em></h1>
            <p class="nb-standfirst">
                Un recorrido en tres capítulos, de lo macro a lo micro: primero la tabla
                completa, después cada variable bajo el microscopio y al final su cara a
                cara con el riesgo. Tres preguntas guían la lectura de todas las figuras.
            </p>
            <span class="nb-stamp">De lo macro<br>a lo micro</span>
            <div class="nb-ficha">
                <strong>{len(df):,}</strong> registros reales &nbsp;·&nbsp;
                <strong>{len(bundle.features)}</strong> variables &nbsp;·&nbsp;
                <strong>{risk_phrase}</strong> &nbsp;·&nbsp;
                {figures_count} figuras en este proceso ({TOTAL_FIGURES_APP} en todo el cuaderno)
            </div>
        </section>
        """
    )


def _render_guiding_questions(hints: tuple[str, str, str]) -> None:
    notes = [
        (
            "uno",
            "¿Cómo está compuesta la base de clientes de Bankify y <mark>qué tan "
            "equilibrada está la variable objetivo</mark> entre clientes cumplidos "
            "y clientes en riesgo?",
            hints[0],
        ),
        (
            "dos",
            "¿Cómo se distribuyen las variables que describen al cliente (montos, "
            "plazos, edad, cupos) y <mark>cuáles presentan atípicos o categorías "
            "dominantes</mark>?",
            hints[1],
        ),
        (
            "tres",
            "Al cruzar las variables con el resultado real, ¿<mark>qué relaciones y "
            "perfiles concentran el mayor riesgo</mark> y cuáles resultan casi "
            "irrelevantes?",
            hints[2],
        ),
    ]
    cards = "".join(
        f"""
        <div class="nb-nota {css}">
            <span class="nb-nota-num">P{index}.</span>
            <p>{text}</p>
            <span class="nb-nota-pista">→ se responde con {hint}</span>
        </div>
        """
        for index, (css, text, hint) in enumerate(notes, start=1)
    )
    _html(f"<div class='nb-notas'>{cards}</div>")
    _html(
        "<p class='nb-notas-pie'>Tres preguntas, catorce figuras: estas son las únicas "
        "preguntas del cuaderno y cubren los dos procesos (6 figuras de aprobación de "
        "crédito y 8 de probabilidad de mora).</p>"
    )


def _render_chapter(number: int) -> None:
    title, copy = CHAPTERS[number]
    _html(
        f"""
        <div class="nb-capitulo">
            <span class="nb-cap-num">{number:02d}</span>
            <div>
                <h3>{title}</h3>
                <p>{copy}</p>
            </div>
        </div>
        """
    )


def _render_data_sheet(bundle: DatasetBundle, risk_rate: float, risk_label: str) -> None:
    features = bundle.df[bundle.features]
    numeric_count = features.select_dtypes(include=["number"]).shape[1]
    categorical_count = len(bundle.features) - numeric_count
    missing = int(features.isna().sum().sum())
    rows = [
        ("Registros", f"{len(bundle.df):,}"),
        ("Variables", f"{len(bundle.features)} ({numeric_count} numéricas · {categorical_count} categóricas)"),
        ("Datos faltantes", f"{missing:,}"),
        (risk_label, f"{risk_rate:.1%}"),
    ]
    body = "".join(
        f"<div class='nb-ficha-fila'><span>{label}</span><strong>{value}</strong></div>"
        for label, value in rows
    )
    _html(
        f"""
        <div class="nb-ficha-tecnica">
            <h4>Ficha técnica de la tabla</h4>
            {body}
        </div>
        """
    )


def _render_figure(index: int, total: int, title: str, note: str, image_path: Path) -> None:
    _html(
        f"""
        <div class="nb-fig-head">
            <span class="nb-fig-num">Fig. {index:02d} / {total:02d}</span>
            <h4>{title}</h4>
        </div>
        """
    )
    if image_path.exists():
        st.image(str(image_path), use_container_width=True)
    else:
        st.warning(f"No se encontró la figura {image_path.name} en app/assets/eda.")
    _html(f"<p class='nb-fig-nota'>{note}</p>")


def _render_table_preview(bundle: DatasetBundle) -> None:
    with st.expander("La tabla en bruto: primeras filas y resumen de las numéricas"):
        st.dataframe(bundle.df.head(10), use_container_width=True)
        numeric = bundle.df.select_dtypes(include=["number"])
        if not numeric.empty:
            st.dataframe(numeric.describe().T.round(2), use_container_width=True)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def render_eda_dashboard(bundle: DatasetBundle) -> None:
    """Renderiza el cuaderno de exploración para el ejercicio activo."""
    _inject_notebook_styles()

    if bundle.exercise == ExerciseOption.CREDIT_APPROVAL:
        figures = GERMAN_FIGURES
        risk_rate = float((bundle.df["credit_outcome"] == 2).mean())
        risk_label = "Créditos malos"
        hints = ("la figura 1", "las figuras 2 a 4", "las figuras 5 y 6")
    else:
        figures = DEFAULT_FIGURES
        risk_rate = float((bundle.df["Default"] == 1).mean())
        risk_label = "Tasa de impago"
        hints = ("la figura 1", "la figura 2", "las figuras 3 a 8")

    total = len(figures)
    _render_masthead(bundle, total, risk_rate)
    _render_guiding_questions(hints)

    chapter_tabs = st.tabs(
        [
            "Capítulo 01 · La tabla",
            "Capítulo 02 · Las variables",
            "Capítulo 03 · Frente al riesgo",
        ]
    )
    for chapter_number, tab in enumerate(chapter_tabs, start=1):
        with tab:
            _render_chapter(chapter_number)
            if chapter_number == 1:
                _render_data_sheet(bundle, risk_rate, risk_label)
            chapter_figures = [
                (index, title, note, filename)
                for index, (filename, chapter, title, note) in enumerate(figures, start=1)
                if chapter == chapter_number
            ]
            if not chapter_figures:
                st.caption(
                    "Este proceso no tiene figuras en este capítulo; su detalle "
                    "está concentrado en los otros dos."
                )
            for index, title, note, filename in chapter_figures:
                _render_figure(index, total, title, note, ASSETS_DIR / filename)
            if chapter_number == 1:
                _render_table_preview(bundle)
            if chapter_number == 3:
                _html(
                    "<p class='nb-cierre'>Fin del recorrido. Si las tres preguntas ya "
                    "tienen respuesta en tu cabeza, baja al cierre y escribe tu hallazgo: "
                    "de la tabla completa al detalle, con tus propias palabras.</p>"
                )
