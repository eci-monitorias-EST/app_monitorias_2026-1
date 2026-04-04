from __future__ import annotations

import pytest

from services.profile_constraints import (
    GRADE_OPTIONS,
    MAX_AGE,
    MIN_AGE,
    SEX_OPTIONS,
    clamp_age,
    get_profile_form_constraints,
    validate_profile_fields,
)


def test_profile_form_constraints_match_requested_ui_limits() -> None:
    constraints = get_profile_form_constraints()

    assert SEX_OPTIONS == ("Masculino", "Femenino")
    assert GRADE_OPTIONS == ("10", "11")
    assert constraints.min_age == MIN_AGE == 14
    assert constraints.max_age == MAX_AGE == 25


@pytest.mark.parametrize(
    ("sexo", "edad", "grado"),
    [
        ("Masculino", 14, "10"),
        ("Femenino", 25, "11"),
    ],
)
def test_validate_profile_fields_accepts_allowed_values(sexo: str, edad: int, grado: str) -> None:
    validate_profile_fields(sexo=sexo, edad=edad, grado=grado)


@pytest.mark.parametrize(
    ("sexo", "edad", "grado"),
    [
        ("", 18, "10"),
        ("Otro", 18, "10"),
        ("Masculino", 13, "10"),
        ("Femenino", 26, "11"),
        ("Femenino", 18, "9"),
    ],
)
def test_validate_profile_fields_rejects_out_of_range_values(sexo: str, edad: int, grado: str) -> None:
    with pytest.raises(ValueError):
        validate_profile_fields(sexo=sexo, edad=edad, grado=grado)


def test_clamp_age_respects_bounds() -> None:
    assert clamp_age(10) == 14
    assert clamp_age(18) == 18
    assert clamp_age(40) == 25
