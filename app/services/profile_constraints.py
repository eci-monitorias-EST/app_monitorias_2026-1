from __future__ import annotations

from dataclasses import dataclass


SEX_OPTIONS: tuple[str, ...] = ("Masculino", "Femenino")
GRADE_OPTIONS: tuple[str, ...] = ("10", "11")
MIN_AGE = 14
MAX_AGE = 25
DEFAULT_AGE = 18


@dataclass(frozen=True)
class ProfileFormConstraints:
    sex_options: tuple[str, ...] = SEX_OPTIONS
    grade_options: tuple[str, ...] = GRADE_OPTIONS
    min_age: int = MIN_AGE
    max_age: int = MAX_AGE
    default_age: int = DEFAULT_AGE


def resolve_option_index(options: tuple[str, ...], current_value: str) -> int:
    return options.index(current_value) if current_value in options else 0


def get_profile_form_constraints() -> ProfileFormConstraints:
    return ProfileFormConstraints()


def clamp_age(value: int) -> int:
    return max(MIN_AGE, min(MAX_AGE, int(value)))


def validate_profile_fields(*, sexo: str, edad: int, grado: str) -> None:
    if sexo not in SEX_OPTIONS:
        raise ValueError(f"Sexo inválido: {sexo}")
    if grado not in GRADE_OPTIONS:
        raise ValueError(f"Grado inválido: {grado}")
    if not MIN_AGE <= int(edad) <= MAX_AGE:
        raise ValueError(f"Edad fuera de rango: {edad}")
