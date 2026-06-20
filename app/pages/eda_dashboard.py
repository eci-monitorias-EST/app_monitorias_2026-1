"""Dashboard exploratorio (EDA) del flujo secuencial.

Presenta los 14 gráficos del EDA tal como fueron construidos en los
notebooks (6 de Aprobación de crédito y 8 de Probabilidad de mora,
servidos desde ``app/assets/eda``), organizados de lo macro (todo el
conjunto) a lo micro (cada dato frente al resultado). El estudiante
saca sus propias conclusiones: no hay textos interpretativos sobre los
gráficos. Cada capítulo tiene una cajita donde el estudiante escribe y
guarda su respuesta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import streamlit as st

from domain.models import ExerciseOption
from services.dashboard_sections import SECTION_LABELS, combine_sections, split_sections
from services.modeling import DatasetBundle

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "eda"

TOTAL_FIGURES_APP = 14

# Glosarios para leer los nombres que vienen impresos dentro de las figuras.
# Las figuras son imágenes fijas, así que no se reconstruyen: el glosario solo
# traduce las siglas para que la audiencia juvenil pueda leer los ejes.
GERMAN_NUMERIC_GLOSSARY = {
    "duration_months": "plazo del crédito (meses)",
    "credit_amount": "monto del crédito",
    "age_years": "edad del solicitante",
    "installment_rate": "tamaño de la cuota",
    "present_residence": "años en la vivienda actual",
    "existing_credits": "créditos que ya tiene",
}

GERMAN_CATEGORICAL_GLOSSARY = {
    "status_checking_account": "estado de la cuenta corriente",
    "credit_history": "historial de pagos previos",
    "purpose": "para qué pidió el crédito",
    "savings_account": "ahorros que tiene",
    "personal_status_sex": "estado civil y sexo",
    "housing": "tipo de vivienda",
}

GERMAN_HEATMAP_GLOSSARY = {
    **GERMAN_NUMERIC_GLOSSARY,
    "present_residence": "años en la vivienda",
    "age_years": "edad",
    "liable_people": "personas a cargo",
    "target": "resultado del crédito",
}

DEFAULT_LIMIT_GLOSSARY = {
    "LIMIT_BAL": "cupo de crédito asignado",
}

DEFAULT_HEATMAP_GLOSSARY = {
    "LIMIT_BAL": "cupo de crédito",
    "AGE": "edad",
    "BILL_AMT1…6": "lo que debía cada mes",
    "PAY_AMT1…6": "lo que pagó cada mes",
    "Default": "resultado (pagó / no pagó)",
}

# Inventario de figuras por ejercicio. Cada figura: archivo, capítulo (1=macro,
# 2=variables, 3=micro), título amigable y un glosario opcional (solo para los
# mapas de calor). No se incluyen notas ni conclusiones: las saca el estudiante.
GERMAN_FIGURES = [
    {"file": "german_credit_01.png", "chapter": 1,
     "title": "¿Cuántos créditos resultaron buenos y cuántos malos?"},
    {"file": "german_credit_02.png", "chapter": 2,
     "title": "¿Cómo se reparten los montos, plazos y edades?",
     "glossary": GERMAN_NUMERIC_GLOSSARY},
    {"file": "german_credit_03.png", "chapter": 2,
     "title": "Identificación de valores atípicos",
     "glossary": GERMAN_NUMERIC_GLOSSARY},
    {"file": "german_credit_04.png", "chapter": 2,
     "title": "Las características más comunes de los solicitantes",
     "glossary": GERMAN_CATEGORICAL_GLOSSARY},
    {"file": "german_credit_05.png", "chapter": 3,
     "title": "Plazo y monto: ¿se diferencian los créditos buenos de los malos?"},
    {"file": "german_credit_06.png", "chapter": 3,
     "title": "Identificación de relaciones entre variables",
     "glossary": GERMAN_HEATMAP_GLOSSARY},
]

DEFAULT_FIGURES = [
    {"file": "default_clients_01.png", "chapter": 1,
     "title": "¿Cuántos clientes pagaron y cuántos no?"},
    {"file": "default_clients_02.png", "chapter": 2,
     "title": "¿Cómo se reparten los cupos de crédito?",
     "glossary": DEFAULT_LIMIT_GLOSSARY},
    {"file": "default_clients_03.png", "chapter": 3,
     "title": "El cupo de crédito frente al pago"},
    {"file": "default_clients_04.png", "chapter": 3,
     "title": "¿Influye la edad en no pagar?"},
    {"file": "default_clients_05.png", "chapter": 3,
     "title": "Cupo promedio según la edad y si pagaron"},
    {"file": "default_clients_06.png", "chapter": 3,
     "title": "Cómo se mueven juntas las variables",
     "glossary": DEFAULT_HEATMAP_GLOSSARY},
    {"file": "default_clients_07.png", "chapter": 3,
     "title": "Identificación de relaciones entre variables",
     "glossary": DEFAULT_HEATMAP_GLOSSARY},
    {"file": "default_clients_08.png", "chapter": 3,
     "title": "Mirando varias variables a la vez"},
]

CHAPTERS = {
    1: "El panorama general",
    2: "Cada dato por separado",
    3: "Buscando relaciones",
}

# Prompts de las cajitas de respuesta (uno por capítulo). Hacen eco de las
# preguntas P1/P2/P3, en lenguaje cercano a la audiencia juvenil.
SECTION_PROMPTS = {
    1: "Con todo el panorama a la vista, ¿qué es lo primero que te llama la "
    "atención del conjunto de datos?",
    2: "Al mirar los datos uno por uno, ¿cuáles te parecen los más interesantes "
    "o los más raros, y por qué?",
    3: "Al cruzar los datos con el resultado, ¿qué relaciones crees que ayudan a "
    "explicar quién es más riesgoso?",
}

# ---------------------------------------------------------------------------
# Estilos (solo este módulo)
# ---------------------------------------------------------------------------
_DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=Caveat:wght@500;600&display=swap');

.eda-hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(115deg, #061b52 0%, #0d3a8f 55%, #155eef 100%);
    border-radius: 14px;
    color: #ffffff;
    margin: 0.4rem 0 1.4rem;
    padding: 1.9rem 2.2rem 1.7rem;
    box-shadow: 0 18px 44px rgba(8, 36, 92, 0.22);
}
.eda-hero::after {
    content: "";
    position: absolute;
    inset: 0 0 0 auto;
    width: 42%;
    background:
        radial-gradient(circle at 78% 22%, rgba(96, 165, 250, 0.35), transparent 55%),
        repeating-linear-gradient(115deg, transparent 0 16px, rgba(96, 165, 250, 0.12) 16px 17px);
}
.eda-hero > * { position: relative; z-index: 1; }
.eda-hero-kicker {
    color: #93c5fd;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    margin: 0 0 0.5rem;
    text-transform: uppercase;
}
.eda-hero h1 {
    color: #ffffff;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 0 0 0.6rem;
    max-width: 82%;
}
.eda-hero p {
    color: rgba(219, 234, 254, 0.92);
    font-size: 1rem;
    line-height: 1.6;
    margin: 0 0 1.05rem;
    max-width: 72%;
}
.eda-hero-pill {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.26);
    border-radius: 999px;
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0 0.4rem 0.35rem 0;
    padding: 0.34rem 0.85rem;
}

.nb-notas {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0.2rem 0 1.1rem;
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

.nb-capitulo {
    align-items: baseline;
    border-bottom: 1px solid #e2ddd0;
    display: flex;
    gap: 1.05rem;
    margin: 0.8rem 0 1.2rem;
    padding-bottom: 0.7rem;
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
    margin: 0;
}

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
    font-size: 1.04rem;
    letter-spacing: 0;
    margin: 0;
    padding-bottom: 0.15rem;
}

.eda-glosa-tag {
    color: #0f2c6b;
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    margin: 0.6rem 0 0.35rem;
    text-transform: uppercase;
}
.eda-glosa {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0 0 0.3rem;
}
.eda-glosa-chip {
    background: #eef2fb;
    border: 1px solid #d6def0;
    border-radius: 6px;
    color: #23324f;
    font-size: 0.8rem;
    padding: 0.28rem 0.62rem;
}
.eda-glosa-chip b { color: #0f2c6b; }

.eda-cajon {
    margin: 1.6rem 0 0.4rem;
}
.eda-cajon-tag {
    background: #0f2c6b;
    border-radius: 999px;
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    padding: 0.26rem 0.72rem;
    text-transform: uppercase;
}
.eda-cajon p {
    color: #101828;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.1rem;
    line-height: 1.4;
    margin: 0.6rem 0 0.5rem;
    max-width: 760px;
}
div[data-testid="stForm"]:has(textarea[aria-label="Tu respuesta del capítulo"]) {
    background: #fffdf7;
    border: 1px solid #e2ddd0;
    border-left: 4px solid #0f2c6b;
    border-radius: 4px;
    box-shadow: 0 8px 20px rgba(15, 44, 107, 0.07);
    padding: 1rem 1.2rem 1.1rem;
}

.eda-chapter-progress {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0 0 1rem;
}
.eda-chapter-pill {
    background: #eef2fb;
    border: 1px solid #d6def0;
    border-radius: 999px;
    color: #5b6b8c;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.32rem 0.85rem;
}
.eda-chapter-pill.active {
    background: #0f2c6b;
    border-color: #0f2c6b;
    color: #ffffff;
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
# Piezas del dashboard
# ---------------------------------------------------------------------------
def _render_hero(bundle: DatasetBundle, figures_count: int) -> None:
    _html(
        f"""
        <section class="eda-hero">
            <p class="eda-hero-kicker">Bankify · Explora los datos</p>
            <h1>¿Qué nos dicen los datos de {bundle.label.lower()}?</h1>
            <p>
                Un recorrido de lo general a lo específico: primero ves toda la
                información junta, luego cada dato por separado y al final cómo se
                conecta con el resultado. Las conclusiones las sacas tú.
            </p>
            <div>
                <span class="eda-hero-pill">{len(bundle.df):,} registros reales</span>
                <span class="eda-hero-pill">{len(bundle.features)} datos por cliente</span>
                <span class="eda-hero-pill">{figures_count} gráficos para explorar</span>
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


def _render_chapter_progress(current_chapter: int) -> None:
    pills = "".join(
        f"<span class='eda-chapter-pill{' active' if number == current_chapter else ''}'>"
        f"{number}. {SECTION_LABELS[number]}</span>"
        for number in (1, 2, 3)
    )
    _html(f"<div class='eda-chapter-progress'>{pills}</div>")


def _render_chapter(number: int) -> None:
    _html(
        f"""
        <div class="nb-capitulo">
            <span class="nb-cap-num">{number:02d}</span>
            <h3>{CHAPTERS[number]}</h3>
        </div>
        """
    )


def _render_glossary(glossary: dict[str, str]) -> None:
    chips = "".join(
        f"<span class='eda-glosa-chip'><b>{code}</b> = {meaning}</span>"
        for code, meaning in glossary.items()
    )
    _html("<p class='eda-glosa-tag'>Qué significa cada nombre del gráfico</p>")
    _html(f"<div class='eda-glosa'>{chips}</div>")


def _render_figure(index: int, total: int, figure: dict, image_path: Path) -> None:
    _html(
        f"""
        <div class="nb-fig-head">
            <span class="nb-fig-num">Fig. {index:02d} / {total:02d}</span>
            <h4>{figure["title"]}</h4>
        </div>
        """
    )
    if image_path.exists():
        st.image(str(image_path), use_container_width=True)
    else:
        st.warning(f"No se encontró la figura {image_path.name} en app/assets/eda.")
    glossary = figure.get("glossary")
    if glossary:
        _render_glossary(glossary)


def _render_figure_card(index: int, total: int, figure: dict, image_path: Path) -> None:
    with st.container(border=True):
        _render_figure(index, total, figure, image_path)


def _render_figure_grid(indexed_figures: list[tuple[int, dict]], total: int, assets_dir: Path) -> None:
    """Muestra las figuras de un capítulo como tarjetas de dashboard.

    Una sola figura se centra en una columna angosta; dos o más se reparten en
    una grilla de 2 columnas. Cada tarjeta tiene su propio borde y un ancho
    contenido (la columna, no la página completa) para que el scroll siempre
    muestre tarjetas enteras en vez de fragmentos de imagen.
    """
    if len(indexed_figures) == 1:
        index, figure = indexed_figures[0]
        _, center_col, _ = st.columns([1, 3, 1])
        with center_col:
            _render_figure_card(index, total, figure, assets_dir / figure["file"])
        return

    columns = st.columns(2)
    for position, (index, figure) in enumerate(indexed_figures):
        with columns[position % 2]:
            _render_figure_card(index, total, figure, assets_dir / figure["file"])


def _render_section_box(
    exercise: str,
    chapter_number: int,
    value: str,
    on_save: Callable[[int, str], bool],
) -> None:
    _html(
        f"""
        <div class="eda-cajon">
            <span class="eda-cajon-tag">Tu turno · Pregunta {chapter_number}</span>
            <p>{SECTION_PROMPTS[chapter_number]}</p>
        </div>
        """
    )
    with st.form(f"eda_section_{exercise}_{chapter_number}"):
        text = st.text_area(
            "Tu respuesta del capítulo",
            value=value,
            height=130,
            label_visibility="collapsed",
            placeholder="Escribe aquí lo que observas...",
        )
        submitted = st.form_submit_button("Guardar mi respuesta")
    if submitted and on_save(chapter_number, text):
        st.success("Respuesta guardada.")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def render_eda_dashboard(
    bundle: DatasetBundle,
    *,
    section_values: dict[int, str],
    on_save: Callable[[int, str], bool],
    current_chapter: int,
) -> None:
    """Renderiza el dashboard exploratorio para el ejercicio activo.

    Muestra un solo capítulo a la vez (controlado por los botones globales
    Siguiente/Anterior en sequential_flow.py) en vez de pestañas, para que esos
    botones puedan recorrer Panorama general → Cada dato → Relaciones antes de
    avanzar a Predicción explicable.
    """
    _inject_dashboard_styles()

    if bundle.exercise == ExerciseOption.CREDIT_APPROVAL:
        figures = GERMAN_FIGURES
        hints = ("la figura 1", "las figuras 2 a 4", "las figuras 5 y 6")
    else:
        figures = DEFAULT_FIGURES
        hints = ("la figura 1", "la figura 2", "las figuras 3 a 8")

    total = len(figures)
    _render_hero(bundle, total)
    _render_guiding_questions(hints)
    _render_chapter_progress(current_chapter)

    _render_chapter(current_chapter)
    indexed_figures = [
        (index, figure)
        for index, figure in enumerate(figures, start=1)
        if figure["chapter"] == current_chapter
    ]
    _render_figure_grid(indexed_figures, total, ASSETS_DIR)
    _render_section_box(
        bundle.exercise,
        current_chapter,
        section_values.get(current_chapter, ""),
        on_save,
    )
