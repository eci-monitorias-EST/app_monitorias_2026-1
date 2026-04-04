# app/services/AGENTS.md

## Contexto

Núcleo de lógica de negocio, persistencia, sincronización remota, modelado, validación y pipelines de texto.

## Responsabilidades

- Encapsular reglas de negocio reutilizables.
- Mantener integraciones externas y pipelines auditables.
- Exponer contratos claros a las páginas.

## Reglas

- Preferir servicios pequeños y testeables.
- Usar logging y manejo explícito de errores en I/O, red y parsing.
- Mantener local-first cuando haya sync remoto, sin confundir éxito local con éxito remoto.
- Si una lógica de estado crece, moverla a una máquina de estados declarativa o estructura dedicada.

## Skills a usar

- `detectar-falsos-positivos`: para validar clasificaciones, respuestas remotas ambiguas, thresholds y estados contradictorios.
- `detectar-procesos-repetitivos`: cuando aparezcan secuencias repetidas de validación, sync, refactor o endurecimiento de contratos.
- `comentarios-3d-incrementales`: cuando haya que trabajar `comment_events`, `comment_hash`, `embeddings_cache`, `projection_cache` o la separación por ejercicio del 3D.
