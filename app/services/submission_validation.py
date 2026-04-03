from __future__ import annotations

from dataclasses import dataclass
import re


PLACEHOLDER_RESPONSES = {
    "-",
    "--",
    "...",
    "n/a",
    "na",
    "ninguno",
    "ninguna",
    "no se",
    "ns",
    "ok",
    "hola",
    "asd",
}


@dataclass(frozen=True)
class TextValidationResult:
    is_valid: bool
    message: str | None = None


class SubmissionValidationService:
    def validate_learning_text(
        self,
        text: str,
        *,
        field_label: str,
        min_length: int = 15,
    ) -> TextValidationResult:
        normalized = self._normalize(text)
        if not normalized:
            return TextValidationResult(False, f"Escribí un {field_label} antes de continuar.")
        if normalized in PLACEHOLDER_RESPONSES:
            return TextValidationResult(
                False,
                f"El {field_label} es demasiado genérico. Escribí una idea concreta.",
            )
        if len(normalized) < min_length:
            return TextValidationResult(
                False,
                f"El {field_label} debe tener al menos {min_length} caracteres significativos.",
            )
        alphanumeric_tokens = re.findall(r"[\wáéíóúñ]+", normalized, flags=re.IGNORECASE)
        if len(alphanumeric_tokens) < 3:
            return TextValidationResult(
                False,
                f"El {field_label} debe incluir una observación mínimamente desarrollada.",
            )
        return TextValidationResult(True)

    def has_meaningful_learning_text(self, text: str, *, min_length: int = 15) -> bool:
        return self.validate_learning_text(
            text,
            field_label="comentario",
            min_length=min_length,
        ).is_valid

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().lower().split())
