"""Codificación de las respuestas por capítulo del dashboard exploratorio.

Las 3 preguntas del dashboard (Panorama general, Cada dato, Relaciones) se
guardan combinadas en un solo campo de texto (``analytics_comment``) usando
marcadores ``【Pn·Etiqueta】``. Vive en services (no en pages) porque tanto el
pipeline de comentarios 3D como la máquina de estados del flujo necesitan
separar las 3 respuestas sin que services dependa de pages.
"""

from __future__ import annotations

import re


SECTION_LABELS: dict[int, str] = {1: "Panorama general", 2: "Cada dato", 3: "Relaciones"}
_SECTION_MARK_RE = re.compile(r"【P([123])·[^】]*】\n?")


def combine_sections(values: dict[int, str]) -> str:
    """Une las tres respuestas en un solo texto persistible (analytics_comment)."""
    parts: list[str] = []
    for number in (1, 2, 3):
        text = (values.get(number) or "").strip()
        if text:
            parts.append(f"【P{number}·{SECTION_LABELS[number]}】\n{text}")
    return "\n\n".join(parts)


def split_sections(combined: str) -> dict[int, str]:
    """Separa el texto combinado en las tres respuestas por capítulo."""
    result = {1: "", 2: "", 3: ""}
    if not combined:
        return result
    matches = list(_SECTION_MARK_RE.finditer(combined))
    if not matches:
        # Texto heredado sin marcadores: lo dejamos en la primera cajita.
        result[1] = combined.strip()
        return result
    for index, match in enumerate(matches):
        number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(combined)
        result[number] = combined[start:end].strip()
    return result
