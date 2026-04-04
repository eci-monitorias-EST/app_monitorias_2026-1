# AGENTS.md

## Purpose

This project is a Python 3.12 application managed with Poetry. It uses Streamlit for the UI, includes data processing and analytics workflows, and must remain testable through `pytest`.

All contributions must prioritize readability, correctness, modularity, and maintainability.

## Core Engineering Rules

1. Follow clean code principles at all times.
2. Type hints are mandatory for all new or modified functions, methods, return values, and important variables.
3. Follow PEP 8.
4. Prefer small, focused functions over large multi-purpose blocks.
5. Keep business logic out of Streamlit page files when possible.
6. Use logging instead of `print`.
7. Error handling is required for all I/O, external requests, parsing, persistence, and user-driven workflows.
8. Every non-trivial change must include or update `pytest` coverage.
9. Favor explicit code over clever shortcuts.
10. Avoid hidden side effects and global mutable state.

## Project Structure

Use the current repository structure as the default organization model:

- `app/main.py`: Streamlit entrypoint only.
- `app/navigation.py`: navigation and page registration.
- `app/pages/`: Streamlit page rendering functions and page-specific UI orchestration.
- `app/components/`: reusable UI components and styling helpers.
- `app/services/`: business logic, data loading, persistence, remote sync, text pipelines, and modeling services.
- `app/domain/`: domain models and shared business entities.
- `app/config/`: configuration access and environment/secret resolution.
- `tests/`: pytest test suite mirroring the behavior of `app/` modules.
- `app_scripts_utils/`: standalone scripts and utilities; keep them isolated from app runtime concerns.

## File Organization Rules

1. Do not place business logic directly in Streamlit pages if it can live in `app/services/` or `app/domain/`.
2. Keep `app/pages/` focused on rendering, user interaction flow, and calling services.
3. Put reusable data transformations, analytics logic, and model orchestration in `app/services/`.
4. Put schemas, typed containers, and domain-specific models in `app/domain/`.
5. Put configuration readers, environment lookups, and secrets access in `app/config/`.
6. Add tests under `tests/` using filenames that mirror the module under test, such as `tests/test_storage.py`.
7. If a module grows beyond a single responsibility, split it rather than adding unrelated helpers.
8. Avoid circular imports by preserving a clear direction: `pages -> services -> domain/config`.

## Naming Conventions

1. Use `snake_case` for variables, functions, and module names.
2. Use `PascalCase` for classes, dataclasses, and domain models.
3. Use `UPPER_SNAKE_CASE` for constants.
4. Name functions with clear verbs, such as `load_credit_approval`, `upsert_feedback`, or `build_navigation`.
5. Name boolean variables with intent, such as `is_valid`, `has_feedback`, or `demo_mode`.
6. Avoid vague names like `data`, `info`, `obj`, `temp`, or `helper` unless the scope is extremely small and obvious.
7. Test names must describe behavior, not implementation details.

## Type Hints

1. All new and modified code must include complete type hints.
2. Prefer concrete types from `collections.abc`, `typing`, and project models.
3. Use `from __future__ import annotations` where it improves forward references and consistency.
4. Do not leave public function signatures untyped.
5. Use domain models or typed structures instead of untyped dictionaries when the shape is stable.

## Logging

1. Never use `print` for application behavior, debugging, or operational tracing.
2. Use the standard `logging` module.
3. Log meaningful events at appropriate levels:
   - `debug` for diagnostic details
   - `info` for normal workflow milestones
   - `warning` for recoverable issues
   - `error` or `exception` for failures
4. Include actionable context in log messages, but never log secrets, tokens, or sensitive user data.

## Error Handling

1. Wrap file I/O, network calls, serialization, parsing, and persistence operations with explicit error handling.
2. Catch specific exceptions instead of broad `except Exception` whenever possible.
3. Fail with clear, actionable messages.
4. Surface user-safe messages in Streamlit pages and log technical details separately.
5. Do not silently swallow exceptions.
6. When recovery is possible, document the fallback behavior in code.

## Streamlit Guidelines

1. Keep Streamlit pages thin and readable.
2. Move transformation logic, analytics calculations, and persistence logic into services.
3. Avoid duplicating widget, state, or layout logic across pages; extract reusable pieces into `app/components/` or `app/services/`.
4. Use Streamlit state intentionally and keep state transitions explicit.
5. Validate user input before passing it to analytics or persistence layers.

## Data Processing And Analytics Guidelines

1. Keep data processing steps deterministic and testable.
2. Separate raw data loading, transformation, modeling, and presentation responsibilities.
3. Prefer pure functions for transformations where possible.
4. Document assumptions about schemas, columns, missing values, and model inputs.
5. Validate inputs before running analytics or prediction workflows.
6. When using external data or models, handle missing files, malformed inputs, and unavailable resources explicitly.

## Testing Rules

1. Use `pytest` for all tests.
2. Every non-trivial behavior change must be covered by tests.
3. Add unit tests for service and domain logic first.
4. Test error paths, not only happy paths.
5. Use fixtures for reusable setup.
6. Keep tests deterministic and isolated from real external systems unless explicitly intended.
7. Prefer small targeted tests over broad end-to-end tests when validating service logic.
8. Use commands such as `poetry run pytest` to validate changes.

## Dependency And Tooling Practices

1. Manage dependencies with Poetry only.
2. Run project commands through Poetry, for example:
   - `poetry install`
   - `poetry run streamlit run app/main.py`
   - `poetry run pytest`
3. Do not introduce new dependencies without a clear justification.
4. Keep dependencies minimal and relevant to the app's analytics and Streamlit scope.

## Git Practices

1. Make focused commits with a single clear purpose.
2. Use descriptive commit messages in the imperative mood.
3. Do not mix refactors, behavior changes, and test-only changes in a single commit unless they are tightly coupled.
4. Run relevant tests before opening a pull request.
5. Keep branches small and reviewable.
6. Never commit secrets, tokens, datasets with sensitive data, or local environment files.
7. Rebase or merge carefully to avoid losing concurrent work.

## Code Review Guidelines

Reviewers and contributors should verify the following:

1. The code follows PEP 8 and existing project structure.
2. Type hints are complete and accurate.
3. Business logic is not unnecessarily embedded in Streamlit UI files.
4. Logging is used appropriately and `print` is absent.
5. Error handling is explicit and user-safe.
6. The change is modular and respects single-responsibility boundaries.
7. Tests cover the new behavior and relevant failure cases.
8. Naming is clear and consistent.
9. The code avoids duplication and unnecessary abstraction.
10. The change does not introduce hidden state, brittle coupling, or unclear side effects.

## Definition Of Done

A change is only considered complete when:

1. The code is clean, modular, typed, and PEP 8 compliant.
2. Logging and error handling are in place where relevant.
3. Tests were added or updated with `pytest`.
4. The implementation fits the repository structure.
5. The change is understandable without extra explanation.

## Local Skills

| Skill | Description | Location |
| --- | --- | --- |
| `administrar-sheet-remoto` | Audita, normaliza y administra el Google Sheet remoto vía Apps Script, incluyendo snapshots, fix legacy y caches. | `skills/administrar-sheet-remoto/SKILL.md` |
| `comentarios-3d-incrementales` | Implementa y mantiene el flujo incremental del gráfico 3D con comment_events, caches y separación por ejercicio. | `skills/comentarios-3d-incrementales/SKILL.md` |
| `imputacion-sintetica-sheet-3d` | Orquesta lotes sintéticos en Google Sheets/Apps Script, render 3D HTML y borrado controlado por batch. | `skills/imputacion-sintetica-sheet-3d/SKILL.md` |
| `detectar-procesos-repetitivos` | Detecta procesos repetidos y obliga a proponer una skill reusable antes de seguir improvisando. | `skills/detectar-procesos-repetitivos/SKILL.md` |
| `detectar-falsos-positivos` | Evalúa si un hallazgo corresponde a un falso positivo, un error válido, un caso ambiguo o ruido no material. | `skills/detectar-falsos-positivos/SKILL.md` |

## Local Skill Usage

1. Usa `detectar-procesos-repetitivos` cuando una misma secuencia de análisis, refactor, validación o sincronización aparezca repetida varias veces en la sesión.
2. Usa `detectar-falsos-positivos` cuando un hallazgo, clasificación, sync remoto o validación pueda estar marcando éxito/error con señales ambiguas o contradictorias.
3. Usa `imputacion-sintetica-sheet-3d` cuando haya que sembrar datos sintéticos en Google Sheets, renderizar HTML 3D con MiniLM+UMAP o preparar borrado seguro por `test_batch_id`.
4. Usa `administrar-sheet-remoto` cuando haya que exportar snapshots, corregir filas legacy, poblar caches o reconstruir proyecciones del Sheet sin depender de la UI de Google Sheets.
5. Usa `comentarios-3d-incrementales` cuando haya que tocar `comment_events`, el gráfico 3D, el resaltado del usuario actual o la separación por ejercicio en comentarios.
6. Si una skill local resuelve mejor el contexto del repo que una instrucción genérica, priorízala antes de improvisar pasos manuales repetidos.
