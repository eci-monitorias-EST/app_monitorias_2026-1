from __future__ import annotations

from services.submission_validation import SubmissionValidationService


def test_validate_learning_text_rejects_blank_placeholder_and_short_values() -> None:
    service = SubmissionValidationService()

    assert service.validate_learning_text("   ", field_label="comentario").is_valid is False
    assert service.validate_learning_text("N/A", field_label="comentario").is_valid is False
    assert service.validate_learning_text("ok", field_label="comentario").is_valid is False
    assert service.validate_learning_text("muy bien", field_label="comentario").is_valid is False


def test_validate_learning_text_accepts_meaningful_response() -> None:
    service = SubmissionValidationService()

    result = service.validate_learning_text(
        "Veo perfiles con montos altos y plazos largos que podrían aumentar el riesgo.",
        field_label="comentario",
    )

    assert result.is_valid is True
    assert result.message is None
