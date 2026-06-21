"""Genera el PDF de retroalimentación final con resultados y opinión por sección.

Vive en services (no en pages) porque construye el documento a partir de
``ParticipantRecord``/``ExerciseProgress`` ya cargados, sin depender de Streamlit.
"""

from __future__ import annotations

import io
import logging
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from domain.models import (
    ExerciseProgress,
    ModelEvaluationResult,
    ParticipantRecord,
    utc_now_iso,
)
from services.dashboard_sections import SECTION_LABELS, split_sections
from services.modeling import DatasetBundle

logger = logging.getLogger(__name__)

_PAGE_WIDTH, _PAGE_HEIGHT = A4
_FOOTER_HEIGHT = 1.3 * cm
_MARGIN = 1.5 * cm

_BANKIFY_NAVY = colors.HexColor("#002d87")
_BANKIFY_BLUE = colors.HexColor("#00c29b")
_BANKIFY_MUTED = colors.HexColor("#4b5563")
_BANKIFY_INK = colors.HexColor("#101828")
_BANKIFY_FAINT = colors.HexColor("#94a3b8")
_BANKIFY_GRID = colors.HexColor("#cbd5f5")


def _draw_footer(canvas: Canvas, _doc: SimpleDocTemplate) -> None:
    """Pie de página de marca: fondo azul oscuro, acento azul y fuente serif para el nombre."""
    canvas.saveState()
    canvas.setFillColor(_BANKIFY_NAVY)
    canvas.rect(0, 0, _PAGE_WIDTH, _FOOTER_HEIGHT, stroke=0, fill=1)
    canvas.setFillColor(_BANKIFY_BLUE)
    canvas.rect(0, _FOOTER_HEIGHT, _PAGE_WIDTH, 0.07 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 12)
    canvas.drawString(_MARGIN, 0.42 * cm, "Bankify")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(
        _MARGIN + 1.55 * cm,
        0.46 * cm,
        "Analytics Lab · laboratorio académico de riesgo crediticio",
    )
    canvas.drawRightString(
        _PAGE_WIDTH - _MARGIN, 0.46 * cm, f"Página {canvas.getPageNumber()}"
    )
    canvas.restoreState()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "bankify-title",
            parent=base["Title"],
            fontName="Times-Bold",
            textColor=_BANKIFY_NAVY,
            alignment=TA_LEFT,
            fontSize=20,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "bankify-subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            textColor=_BANKIFY_MUTED,
            fontSize=9.5,
            spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "bankify-section",
            parent=base["Heading2"],
            fontName="Times-Bold",
            textColor=_BANKIFY_BLUE,
            fontSize=13,
            spaceBefore=16,
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "bankify-label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_BANKIFY_NAVY,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "bankify-body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=_BANKIFY_INK,
            leading=14,
            spaceAfter=10,
        ),
        "empty": ParagraphStyle(
            "bankify-empty",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            textColor=_BANKIFY_FAINT,
            spaceAfter=10,
        ),
    }


def _opinion_paragraph(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    clean = text.strip()
    if not clean:
        return Paragraph("Sin respuesta registrada.", styles["empty"])
    safe = escape(clean).replace("\n", "<br/>")
    return Paragraph(safe, styles["body"])


def _metrics_table(evaluation: ModelEvaluationResult) -> Table:
    table = Table(
        [
            ["Exactitud", "Precisión", "Exhaustividad", "F1-Score"],
            [
                f"{evaluation.accuracy:.1%}",
                f"{evaluation.precision:.1%}",
                f"{evaluation.recall:.1%}",
                f"{evaluation.f1:.1%}",
            ],
        ],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BANKIFY_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, _BANKIFY_GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_feedback_report_pdf(
    *,
    participant: ParticipantRecord,
    bundle: DatasetBundle,
    progress: ExerciseProgress,
    evaluation: ModelEvaluationResult | None,
) -> bytes:
    """Construye el PDF de retroalimentación final con resultados y opinión por sección."""
    styles = _build_styles()
    participant_name = escape(
        str(participant.profile.get("nombre", "")).strip() or participant.public_alias
    )
    generated_at = utc_now_iso()[:19].replace("T", " ")

    story: list = [
        Paragraph("Bankify Analytics Lab", styles["title"]),
        Paragraph(
            f"Reporte de aprendizaje · {escape(bundle.label)}", styles["subtitle"]
        ),
        Paragraph(
            f"Participante: <b>{participant_name}</b> | "
            f"Código: {escape(participant.access_code_display)} | "
            f"Generado: {generated_at} UTC",
            styles["subtitle"],
        ),
        Spacer(1, 6),
    ]

    story.append(Paragraph("1. Diccionario de datos", styles["section"]))
    story.append(
        Paragraph(f"Variables analizadas: {len(bundle.descriptors)}", styles["label"])
    )
    story.append(
        Paragraph("Tu opinión: ¿qué le sugiere el conjunto de datos?", styles["label"])
    )
    story.append(_opinion_paragraph(progress.dataset_comment, styles))

    story.append(Paragraph("2. Exploración y dashboard", styles["section"]))
    sections = split_sections(progress.analytics_comment)
    for number, label in SECTION_LABELS.items():
        story.append(Paragraph(f"Tu opinión · {label}", styles["label"]))
        story.append(_opinion_paragraph(sections.get(number, ""), styles))

    story.append(Paragraph("3. Predicción explicable", styles["section"]))
    if evaluation is not None:
        story.append(
            Paragraph(
                f"Modelo evaluado: {escape(evaluation.model_name)}", styles["label"]
            )
        )
        story.append(_metrics_table(evaluation))
        story.append(Spacer(1, 10))
    prediction_output = progress.prediction_output or {}
    if prediction_output:
        probability = prediction_output.get("probability")
        probability_text = (
            f"{probability:.1%}" if isinstance(probability, (int, float)) else "N/D"
        )
        label = escape(str(prediction_output.get("label", "N/D")))
        story.append(
            Paragraph(
                f"Resultado de tu simulación: <b>{label}</b> (confianza: {probability_text})",
                styles["body"],
            )
        )
    else:
        story.append(
            Paragraph(
                "No se ejecutó ninguna simulación de predicción.", styles["empty"]
            )
        )
    story.append(
        Paragraph(
            "Tu opinión: ¿qué entendiste de la explicación del modelo?", styles["label"]
        )
    )
    story.append(_opinion_paragraph(progress.prediction_reflection, styles))

    story.append(Paragraph("4. Retroalimentación final", styles["section"]))
    feedback = progress.feedback
    if feedback is not None:
        story.append(
            Paragraph(
                f"Calificación otorgada: {feedback.rating} de 5 estrellas",
                styles["label"],
            )
        )
        story.append(Paragraph("Resumen de la experiencia", styles["label"]))
        story.append(_opinion_paragraph(feedback.summary, styles))
        if feedback.missing_topics:
            story.append(
                Paragraph(
                    "¿Qué faltó para que la experiencia fuera mejor?", styles["label"]
                )
            )
            story.append(_opinion_paragraph(feedback.missing_topics, styles))
        if feedback.improvement_ideas:
            story.append(Paragraph("¿Qué deberíamos mejorar?", styles["label"]))
            story.append(_opinion_paragraph(feedback.improvement_ideas, styles))
    else:
        story.append(Paragraph("Retroalimentación aún no registrada.", styles["empty"]))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_FOOTER_HEIGHT + 0.4 * cm,
        pageCompression=0,
    )
    try:
        doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    except Exception:
        logger.exception("No fue posible generar el PDF de retroalimentación final.")
        raise
    return buffer.getvalue()
