# notebooks/AGENTS.md

## Contexto

Exploración ad hoc, análisis manual y prototipos en notebooks.

## Responsabilidades

- Permitir exploración rápida sin contaminar el runtime principal.
- Servir como espacio de experimentación antes de bajar lógica a servicios o scripts.

## Reglas

- No dejar lógica crítica viviendo solo en notebooks.
- Si un hallazgo o pipeline se estabiliza, migrarlo a `app/services/` o `app_scripts_utils/`.
- Mantener notebooks entendibles y orientados a análisis, no a infraestructura del producto.

## Skills a usar

- `detectar-procesos-repetitivos`: cuando un análisis manual repetido de notebook amerite script o skill.
- `detectar-falsos-positivos`: cuando una visualización o métrica exploratoria pueda llevar a conclusiones ambiguas.
