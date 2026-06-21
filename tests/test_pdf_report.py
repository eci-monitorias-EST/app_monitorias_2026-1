from __future__ import annotations

from dataclasses import dataclass

from domain.models import (
    ExerciseProgress,
    FeedbackRecord,
    ModelEvaluationResult,
    ParticipantRecord,
    VariableDescriptor,
)
from services.dashboard_sections import combine_sections
from services.pdf_report import build_feedback_report_pdf


@dataclass
class _FakeBundle:
    exercise: str
    label: str
    descriptors: list[VariableDescriptor]


def _build_participant() -> ParticipantRecord:
    return ParticipantRecord(
        participant_id="p1",
        access_code_hash="hash",
        public_alias="alias-1",
        profile={"nombre": "Ana Rivera"},
        access_code_display="ABC123",
    )


def _build_bundle() -> _FakeBundle:
    descriptors = [
        VariableDescriptor(
            "duration_months", "Duración del crédito", "desc", "numeric", "fuente"
        ),
        VariableDescriptor(
            "credit_amount", "Monto del crédito", "desc", "numeric", "fuente"
        ),
    ]
    return _FakeBundle(
        exercise="credit_approval",
        label="Aprobación de crédito",
        descriptors=descriptors,
    )


def _build_evaluation() -> ModelEvaluationResult:
    return ModelEvaluationResult(
        exercise="credit_approval",
        model_name="Regresión logística",
        accuracy=0.82,
        precision=0.79,
        recall=0.75,
        f1=0.77,
        confusion_matrix=[[50, 10], [8, 32]],
        class_labels=("Rechazado", "Aprobado"),
        shap_importance=[{"feature": "duration_months", "importance": 0.3}],
        test_size=100,
    )


def test_build_feedback_report_pdf_returns_a_valid_pdf_with_section_content() -> None:
    progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment="Este dataset muestra patrones claros de riesgo crediticio.",
        analytics_comment=combine_sections(
            {
                1: "El panorama general muestra mas solicitudes aprobadas que rechazadas.",
                2: "Cada variable aporta contexto distinto sobre el solicitante.",
                3: "Las relaciones entre variables sugieren correlacion entre ingresos y mora.",
            }
        ),
        prediction_reflection="Entendi que el monto del credito es la variable mas determinante.",
        prediction_output={
            "label": "Aprobado",
            "probability": 0.87,
            "provider": "logistic_regression",
        },
        feedback=FeedbackRecord(
            rating=5, summary="Actividad muy clara y bien explicada."
        ),
    )

    pdf_bytes = build_feedback_report_pdf(
        participant=_build_participant(),
        bundle=_build_bundle(),
        progress=progress,
        evaluation=_build_evaluation(),
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert b"Bankify" in pdf_bytes
    assert b"Este dataset muestra patrones claros de riesgo crediticio." in pdf_bytes
    assert b"Aprobado" in pdf_bytes


def test_build_feedback_report_pdf_handles_missing_opinions_and_no_evaluation() -> None:
    progress = ExerciseProgress(exercise="default_risk")

    pdf_bytes = build_feedback_report_pdf(
        participant=_build_participant(),
        bundle=_build_bundle(),
        progress=progress,
        evaluation=None,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert b"Sin respuesta registrada." in pdf_bytes
    assert (
        b"Retroalimentacion aun no registrada." not in pdf_bytes
    )  # se escribe con tilde, no se busca acento aqui


def test_build_feedback_report_pdf_escapes_free_text_without_raising() -> None:
    progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment='Texto con <tag> riesgoso & comillas "raras" que no debe romper el XML interno.',
        feedback=FeedbackRecord(
            rating=2,
            summary="Resumen con & < > caracteres especiales.",
            missing_topics="Faltó <b>profundidad</b>",
            improvement_ideas="Usar & explicar mejor los <modelos>",
        ),
    )

    pdf_bytes = build_feedback_report_pdf(
        participant=_build_participant(),
        bundle=_build_bundle(),
        progress=progress,
        evaluation=None,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 0
