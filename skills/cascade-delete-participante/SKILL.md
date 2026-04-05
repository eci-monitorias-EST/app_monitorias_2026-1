---
name: cascade-delete-participante
description: >
  Elimina en cascada todos los registros de un participante del Google Sheet
  respetando el orden de FK (children primero, sesiones último).
  Trigger: cuando haya que borrar un participante de prueba, resetear datos de un participante
  específico o limpiar registros corruptos sin dejar huérfanos en otras hojas.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando hay que borrar todos los datos de un participante específico (prueba, corrupto, duplicado).
- Cuando querés resetear un participante sin tocar el resto del Sheet.
- Cuando borraste el `app_state.json` local y necesitás limpiar también el Sheet remoto.

## Critical Patterns

- **Orden FK es obligatorio**: comment_events → respuestas → feedback → historial_comentarios → control_ingreso → sesiones
- Siempre corré dry-run primero para ver qué filas se van a borrar.
- Los caches (`embeddings_cache`, `projection_cache`) son opt-in con `--include-caches` — por defecto NO se borran (pueden servir a otros participantes con el mismo comment_hash).
- La confirm phrase es `CASCADE_DELETE_PARTICIPANT` y es obligatoria para ejecutar.
- Si un sheet falla, el cascade se detiene — no sigue borrando los siguientes.

## Workflow

1. Dry-run para ver el plan:
   ```bash
   poetry run python app_scripts_utils/sheet_admin_actions.py \
     cascade-delete-participant \
     --participant-id <PID>
   ```
2. Si querés también limpiar caches:
   ```bash
   poetry run python app_scripts_utils/sheet_admin_actions.py \
     cascade-delete-participant \
     --participant-id <PID> \
     --include-caches
   ```
3. Ejecutar el borrado real:
   ```bash
   poetry run python app_scripts_utils/sheet_admin_actions.py \
     cascade-delete-participant \
     --participant-id <PID> \
     --execute \
     --confirm-phrase CASCADE_DELETE_PARTICIPANT
   ```

## Cascade Order

| Paso | Hoja | FK |
|------|------|----|
| 1 | `comment_events` | participant_id |
| 2 | `respuestas` | participant_id |
| 3 | `feedback` | participant_id |
| 4 | `historial_comentarios` | participant_id |
| 5 | `control_ingreso` | participant_id |
| 6 | `sesiones` | participant_id (PK) |
| 7* | `embeddings_cache` | participant_id (opt-in) |
| 8* | `projection_cache` | participant_id (opt-in) |

*Solo con `--include-caches`

## Case Map

| Situación | Acción |
|-----------|--------|
| Borrar participante de prueba | cascade-delete-participant + --execute |
| Borrar y limpiar caches | cascade-delete-participant + --include-caches + --execute |
| Ver qué se borraría sin tocar nada | cascade-delete-participant (sin --execute) |
| El cascade falló a mitad | Ver qué sheets se completaron en results[], repetir desde el sheet que falló con clear-sheet-rows |

## Commands

```bash
# Dry-run (sin --execute = siempre seguro)
poetry run python app_scripts_utils/sheet_admin_actions.py \
  cascade-delete-participant \
  --participant-id PARTICIPANT_ID_AQUI

# Dry-run incluyendo caches
poetry run python app_scripts_utils/sheet_admin_actions.py \
  cascade-delete-participant \
  --participant-id PARTICIPANT_ID_AQUI \
  --include-caches

# Ejecución real
poetry run python app_scripts_utils/sheet_admin_actions.py \
  cascade-delete-participant \
  --participant-id PARTICIPANT_ID_AQUI \
  --execute \
  --confirm-phrase CASCADE_DELETE_PARTICIPANT
```

## Resources

- `app_scripts_utils/sheet_admin_actions.py` — implementación del cascade
- `app_scripts_utils/webapp_client.py` — `clear_sheet_rows` que usa internamente
- `app_scripts_utils/google_sync_webapp.gs` — Apps Script que recibe `clear_sheet_rows`
