---
name: imputacion-sintetica-sheet-3d
description: >
  Orquesta pruebas masivas con datos sintéticos en Google Sheets/Apps Script,
  incluyendo seed, lectura por lote, vectorización MiniLM, reducción UMAP,
  exportación HTML 3D y borrado controlado por batch. Trigger: cuando haya
  que poblar el Sheet con datos ficticios, validar el flujo remoto o generar
  visualizaciones 3D fuera de la UI principal.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando quieras poblar Google Sheets con datos ficticios para pruebas controladas.
- Cuando necesites generar una visualización 3D HTML sin pasar por Streamlit.
- Cuando quieras validar el contrato Apps Script ↔ app antes de tocar datos reales.
- Cuando necesites un borrado controlado por lote de prueba (`test_batch_id`).

## Critical Patterns

- TODO dato sintético debe quedar marcado con:
  - `is_test_data = true`
  - `test_batch_id`
  - `data_origin = synthetic_mass_imputation`
- Nunca ejecutes `delete` real sin confirmación explícita del usuario.
- Siempre corré `delete-dry-run` antes de cualquier borrado real.
- Si cambia el Apps Script, redeployá y validá la nueva URL `/exec` antes de sembrar.
- Si el 3D falla con pocos puntos, usar el fallback determinístico del pipeline actual.

## Workflow

1. Verificar URL/token activos del webapp.
2. Sembrar lote sintético con `seed --test-batch-id ...`.
3. Consultar/validar el batch remoto.
4. Generar HTML 3D con `render --exercise ...`.
5. Ejecutar `delete-dry-run` para verificar alcance del borrado.
6. Solo si el usuario lo ordena, ejecutar `delete --execute`.

## Commands

```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py seed --test-batch-id demo-lote-001

poetry run python app_scripts_utils/synthetic_sheet_imputation.py render --test-batch-id demo-lote-001 --exercise default_risk

poetry run python app_scripts_utils/synthetic_sheet_imputation.py render --test-batch-id demo-lote-001 --exercise credit_approval

poetry run python app_scripts_utils/synthetic_sheet_imputation.py delete-dry-run --test-batch-id demo-lote-001

poetry run python app_scripts_utils/synthetic_sheet_imputation.py delete --test-batch-id demo-lote-001 --execute
```

## Key Files

- `app/services/synthetic_imputation.py` — construcción de lotes y exportación HTML.
- `app_scripts_utils/synthetic_sheet_imputation.py` — CLI de seed/render/delete.
- `app_scripts_utils/synthetic_sheet_imputation_dataset.json` — dataset ficticio versionable.
- `app_scripts_utils/google_sync_webapp.gs` — Apps Script con soporte de lotes sintéticos.

## Example

```text
Necesito poblar el Sheet con un lote ficticio para probar MiniLM + UMAP + gráfico 3D,
pero dejando la puerta abierta para borrar solo esos datos después.

=> Cargar la skill `imputacion-sintetica-sheet-3d`
=> Sembrar un `test_batch_id`
=> Generar HTML por ejercicio
=> Hacer dry-run de borrado
=> Esperar confirmación del usuario antes del delete real
```
