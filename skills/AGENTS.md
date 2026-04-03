# skills/AGENTS.md

## Contexto

Skills locales del proyecto para guiar al agente en patrones específicos del repositorio.

## Responsabilidades

- Definir triggers claros y reglas críticas reutilizables.
- Mantener skills cortas, accionables y no redundantes.

## Reglas

- Cada skill debe resolver un patrón realmente repetible.
- Si una skill deja de representar la realidad del repo, actualizarla junto con `AGENTS.md`.
- Si aparece un patrón repetitivo nuevo, usar `detectar-procesos-repetitivos` y luego `skill-creator` para materializarlo.

## Skills a usar

- `detectar-procesos-repetitivos`: para decidir cuándo conviene crear nuevas skills.
- `detectar-falsos-positivos`: cuando una skill trate validaciones o clasificaciones susceptibles a señales ambiguas.
- `imputacion-sintetica-sheet-3d`: cuando el patrón reusable sea poblar Sheets con datos sintéticos, visualizar 3D fuera de Streamlit y borrar por lote de prueba.
