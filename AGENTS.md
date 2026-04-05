# Repository Guidelines

## How to Use This Guide

- Start here for cross-project norms.
- The `skills/` directory contains project-specific skills with detailed patterns.
- When an action matches an Auto-invoke entry, load that skill FIRST before writing any code.

---

## Available Skills

Use these skills for detailed patterns on-demand:

### Generic Skills (Any Project)
| Skill | Description | URL |
|-------|-------------|-----|
| `pytest` | Fixtures, mocking, markers, parametrize | [SKILL.md](skills/pytest/SKILL.md) |
| `skill-creator` | Create new AI agent skills | [SKILL.md](skills/skill-creator/SKILL.md) |
| `skill-sync` | Sync skill metadata to AGENTS.md auto-invoke sections | [SKILL.md](skills/skill-sync/SKILL.md) |

### Project-Specific Skills
| Skill | Description | URL |
|-------|-------------|-----|
| `administrar-sheet-remoto` | Auditar, normalizar y administrar el Google Sheet remoto vía Apps Script, incluyendo snapshots, fix legacy y caches | [SKILL.md](skills/administrar-sheet-remoto/SKILL.md) |
| `comentarios-3d-incrementales` | Flujo incremental de comment_events, embeddings_cache, projection_cache y gráfico 3D con separación por ejercicio | [SKILL.md](skills/comentarios-3d-incrementales/SKILL.md) |
| `detectar-falsos-positivos` | Evaluar si un hallazgo del pipeline es falso positivo, error válido, ambiguo o ruido no material | [SKILL.md](skills/detectar-falsos-positivos/SKILL.md) |
| `detectar-procesos-repetitivos` | Detectar patrones repetidos y proponer nuevas skills antes de seguir improvisando | [SKILL.md](skills/detectar-procesos-repetitivos/SKILL.md) |
| `imputacion-sintetica-sheet-3d` | Poblar Sheets con datos sintéticos, validar flujo remoto y generar visualizaciones 3D HTML | [SKILL.md](skills/imputacion-sintetica-sheet-3d/SKILL.md) |
| `cascade-delete-participante` | Eliminar en cascada todos los registros de un participante respetando el orden de FK | [SKILL.md](skills/cascade-delete-participante/SKILL.md) |

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| After creating/modifying a skill | `skill-sync` |
| Regenerate AGENTS.md Auto-invoke tables (sync.sh) | `skill-sync` |
| Troubleshoot why a skill is missing from AGENTS.md auto-invoke | `skill-sync` |
| Creating new skills | `skill-creator` |
| Working on the 3D graph, comment_events, embeddings_cache or projection_cache | `comentarios-3d-incrementales` |
| Modifying the sequential flow or per-exercise state | `comentarios-3d-incrementales` |
| Exporting snapshots, repairing legacy rows or managing remote Sheet caches | `administrar-sheet-remoto` |
| Seeding synthetic data into Google Sheets or generating 3D HTML outside Streamlit | `imputacion-sintetica-sheet-3d` |
| Validating or deleting a synthetic test batch | `imputacion-sintetica-sheet-3d` |
| Evaluating predictions, classification results or pipeline findings for correctness | `detectar-falsos-positivos` |
| Deleting a participant's data from Google Sheets | `cascade-delete-participante` |
| Resetting a participant or cleaning up corrupted/test participant records in the Sheet | `cascade-delete-participante` |
| A pattern or workflow has appeared 3 or more times in a session | `detectar-procesos-repetitivos` |
| Writing Python tests with pytest | `pytest` |

---

## Project Overview

App de Monitorias 2026-1 — aplicación Streamlit para recolección de datos pedagógicos, análisis de comentarios con embeddings, visualización 3D y predicción de riesgo crediticio/mora.

| Component | Location | Tech Stack |
|-----------|----------|------------|
| App Streamlit | `app/` | Python 3.12, Streamlit, Plotly |
| Servicios | `app/services/` | scikit-learn, UMAP, sentence-transformers, LangGraph |
| Scripts CLI | `app_scripts_utils/` | Python CLI, Google Apps Script (webapp) |
| Tests | `tests/` | pytest |
| Skills | `skills/` | AI agent skill files |

### Project Structure

- `app/main.py`: Streamlit entrypoint only.
- `app/navigation.py`: navigation and page registration.
- `app/pages/`: Streamlit page rendering functions and page-specific UI orchestration.
- `app/components/`: reusable UI components and styling helpers.
- `app/services/`: business logic, data loading, persistence, remote sync, text pipelines, and modeling services.
- `app/domain/`: domain models and shared business entities.
- `app/config/`: configuration access and environment/secret resolution.
- `tests/`: pytest test suite mirroring the behavior of `app/` modules.
- `app_scripts_utils/`: standalone scripts and utilities; keep them isolated from app runtime concerns.

### Key Architecture Decisions

- `respuestas` es la fuente consolidada por ejercicio; `comment_events` es la fuente para el gráfico 3D.
- `comment_hash` identifica un texto de comentario; el upsert lógico usa `participant_id + exercise + comment_type`.
- Los caches remotos (`embeddings_cache`, `projection_cache`) son idempotentes por `comment_hash`.
- El Apps Script actúa como API remota; si cambia, hay que redeployar antes de usar acciones nuevas.
- `is_test_data = true` + `test_batch_id` marcan datos sintéticos; nunca mezclar con reales sin confirmar.
- Dependency direction: `pages -> services -> domain/config`. No circular imports.

---

## Core Engineering Rules

1. Follow clean code principles at all times.
2. Type hints are mandatory for all new or modified functions, methods, return values, and important variables.
3. Follow PEP 8.
4. Prefer small, focused functions over large multi-purpose blocks.
5. Keep business logic out of Streamlit page files — place it in `app/services/` or `app/domain/`.
6. Use `logging` instead of `print`.
7. Error handling is required for all I/O, external requests, parsing, persistence, and user-driven workflows.
8. Every non-trivial change must include or update `pytest` coverage.
9. Favor explicit code over clever shortcuts.
10. Avoid hidden side effects and global mutable state.

### Naming Conventions

- `snake_case` for variables, functions, and module names.
- `PascalCase` for classes, dataclasses, and domain models.
- `UPPER_SNAKE_CASE` for constants.
- Name functions with clear verbs: `load_credit_approval`, `upsert_feedback`, `build_navigation`.
- Name booleans with intent: `is_valid`, `has_feedback`, `demo_mode`.
- Avoid vague names like `data`, `info`, `obj`, `temp`, or `helper`.
- Test names must describe behavior, not implementation details.

### Streamlit Guidelines

- Keep Streamlit pages thin and readable.
- Move transformation, analytics, and persistence logic into services.
- Avoid duplicating widget or state logic across pages; extract into `app/components/` or `app/services/`.
- Use Streamlit state intentionally and keep state transitions explicit.
- Validate user input before passing it to analytics or persistence layers.

### Error Handling

- Wrap file I/O, network calls, serialization, parsing, and persistence with explicit error handling.
- Catch specific exceptions instead of broad `except Exception` whenever possible.
- Surface user-safe messages in Streamlit pages; log technical details separately.
- Do not silently swallow exceptions.

---

## Python Development

```bash
# Setup
poetry install --with dev

# Run app
poetry run streamlit run app/main.py

# Tests
poetry run pytest
poetry run pytest tests/test_comment_events.py  # test file específico

# Linting
poetry run black .
```

---

## Commit & Pull Request Guidelines

Follow conventional-commit style: `<type>[scope]: <description>`

**Types:** `feat`, `fix`, `docs`, `chore`, `perf`, `refactor`, `style`, `test`

Before creating a PR:
1. Run all relevant tests: `poetry run pytest`
2. Verify no synthetic data (`is_test_data = true`) was left in production sheets
3. Link screenshots for UI changes
4. Never commit secrets, tokens, datasets with sensitive data, or local environment files
