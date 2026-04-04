---
name: comentarios-3d-incrementales
description: >
  Implementa y mantiene el flujo incremental de comentarios 3D con eventos
  individuales, comment_hash, caches remotos de embeddings/proyección y
  resaltado del usuario actual. Trigger: cuando haya que trabajar el gráfico 3D,
  comment_events, embeddings_cache, projection_cache o separación por ejercicio.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando haya que modificar el gráfico 3D de comentarios.
- Cuando el origen de datos sea `comment_events` en vez de `respuestas` consolidadas.
- Cuando haya que agregar o depurar `comment_hash`, `embeddings_cache` o `projection_cache`.
- Cuando haya que asegurar separación por ejercicio (`default_risk` vs `credit_approval`).

## Critical Patterns

- El 3D debe usar comentarios individuales (`dataset_comment`, `analytics_comment`, `prediction_reflection`) en un solo gráfico.
- Color = `comment_type`; resaltado del usuario actual = tamaño/símbolo/borde, no otro color distinto.
- `comment_events` debe hacer upsert por `participant_id + exercise + comment_type`.
- `comment_hash` cambia con el texto, pero NO debe generar una fila lógica nueva del mismo tipo.
- `respuestas` sigue siendo la fuente consolidada para otros usos; `comment_events` es la fuente del 3D.
- Si falta cache/proyección, recalcular el lote visible actual y upsertearlo es aceptable en esta primera versión.

## Workflow recomendado

1. Guardar progreso consolidado por ejercicio en `respuestas`.
2. Derivar eventos individuales en `comment_events`.
3. Generar `clean_comment` y `comment_hash`.
4. Revisar `embeddings_cache`:
   - si existe por `exercise + comment_hash + embedding_version`, reutilizar;
   - si no, calcular MiniLM y guardar.
5. Revisar `projection_cache`:
   - si existe por `exercise + comment_hash + projection_version`, reutilizar;
   - si no, recalcular el lote visible y hacer upsert.
6. Construir el gráfico 3D:
   - color por `comment_type`
   - resaltado del usuario por `participant_id`

## Case Map

| Situación | Acción |
| --- | --- |
| Un comentario editado crea filas duplicadas | Verificar upsert de `comment_events` por `participant_id + exercise + comment_type` |
| El gráfico mezcla mora y crédito | Verificar query/remoto filtrado por `exercise` |
| El usuario no se resalta | Verificar `participant_id == current_participant_id` al construir puntos |
| El gráfico está lento | Revisar caches remotos y recalcular solo el lote visible |
| Faltan colores por tipo | Verificar mapeo `comment_type -> color/symbol` en la UI |

## Commands

```bash
poetry run pytest tests/test_comment_events.py tests/test_text_pipeline.py tests/test_session_service.py tests/test_storage.py

poetry run python app_scripts_utils/sheet_snapshot_export.py \
  --sheet respuestas \
  --sheet comment_events \
  --sheet embeddings_cache \
  --sheet projection_cache \
  --limit-rows 20 \
  --snapshot-label comments-3d-audit
```

## Resources

- `app/services/comment_events.py`
- `app/services/text_pipeline.py`
- `app/pages/sequential_flow.py`
- `app/services/session_service.py`
- `app_scripts_utils/google_sync_webapp.gs`
