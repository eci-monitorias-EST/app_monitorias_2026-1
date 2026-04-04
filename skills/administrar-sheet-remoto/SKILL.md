---
name: administrar-sheet-remoto
description: >
  Audita, normaliza y administra el Google Sheet remoto vía Apps Script/webapp,
  incluyendo snapshots, reparación de filas legacy, backfill de caches y
  reconstrucción de proyecciones 3D. Trigger: cuando haya que inspeccionar,
  corregir o mantener el contenido del Sheet sin depender de la UI de Google Sheets.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando necesitás exportar snapshots controlados del Sheet para auditar contenido.
- Cuando hay filas `legacy` con columnas corridas o contratos viejos.
- Cuando querés poblar `embeddings_cache` o `projection_cache` sin tocar la UI.
- Cuando necesitás limpiar filas auxiliares o reconstruir proyecciones por versión.

## Critical Patterns

- No operes a ciegas: primero exportá snapshot.
- Las acciones destructivas requieren confirmación explícita.
- `respuestas` es la fuente consolidada; `historial_comentarios` queda para auditoría.
- No mezcles datos legacy con caches nuevas sin normalizar o archivar antes.
- Cuando el Apps Script cambia, hay que redeployar la Web App antes de usar las acciones nuevas.

## Workflow recomendado

1. Exportar snapshot con `sheet_snapshot_export.py`.
2. Clasificar el problema:
   - legacy → `fix_legacy_rows` / `archive_legacy_rows`
   - feedback roto → `normalize_feedback_schema`
   - cache vacía → `backfill_embeddings_cache`
   - proyección stale → `rebuild_projection_cache`
   - limpiar versión vieja → `clear_sheet_rows`
3. Ejecutar primero dry-run o preview.
4. Ejecutar la acción real solo con confirmación cuando corresponda.
5. Reexportar snapshot para verificar el resultado.

## Case Map

| Problema | Acción |
| --- | --- |
| Filas viejas con columnas corridas | `fix-legacy-rows` |
| Feedback guardado con esquema viejo | `normalize-feedback-schema` |
| Legacy que no querés mezclar con el flujo nuevo | `archive-legacy-rows` |
| Cache de proyección vieja o inválida | `clear-sheet-rows` |
| Quiero llenar `embeddings_cache` desde filas ya preparadas | `backfill-embeddings-cache` |
| Quiero regenerar `projection_cache` desde puntos proyectados | `rebuild-projection-cache` |

## Commands

```bash
poetry run python app_scripts_utils/sheet_snapshot_export.py \
  --sheet sesiones \
  --sheet respuestas \
  --sheet historial_comentarios \
  --sheet feedback \
  --sheet control_ingreso \
  --sheet embeddings_cache \
  --sheet projection_cache \
  --limit-rows 20 \
  --snapshot-label current-sheet-audit

poetry run python app_scripts_utils/sheet_admin_actions.py \
  fix-legacy-rows \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json

poetry run python app_scripts_utils/sheet_admin_actions.py \
  normalize-feedback-schema \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json \
  --exercise credit_approval

poetry run python app_scripts_utils/sheet_admin_actions.py \
  archive-legacy-rows \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json \
  --archive-reason legacy_snapshot_cleanup \
  --execute \
  --confirm-phrase ARCHIVE_LEGACY_ROWS

poetry run python app_scripts_utils/sheet_admin_actions.py \
  clear-sheet-rows \
  --sheet projection_cache \
  --exercise credit_approval \
  --projection-version projection-v3 \
  --execute \
  --confirm-phrase CLEAR_SHEET_ROWS
```

## Resources

- `app_scripts_utils/google_sync_webapp.gs`
- `app_scripts_utils/webapp_client.py`
- `app_scripts_utils/sheet_snapshot_export.py`
- `app_scripts_utils/sheet_admin_actions.py`
- `README.md` sección de herramientas administrativas del Sheet
