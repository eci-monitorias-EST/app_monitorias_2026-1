# data/AGENTS.md

## Contexto

Datos de entrada, artifacts procesados y archivos auxiliares del proyecto.

## Responsabilidades

- Conservar datasets y outputs necesarios para el funcionamiento o análisis.
- Evitar mezclar estado local efímero con data que sí deba versionarse.

## Reglas

- No commitear datos sensibles.
- No asumir que `data/processed/` debe versionarse por defecto; distinguir artifacts reproducibles de estado local.
- Si un archivo cambia en cada ejecución local, considerar ignorarlo o regenerarlo.

## Skills a usar

- `detectar-falsos-positivos`: cuando una lectura de datos o artifact pueda inducir una conclusión equivocada por ruido o estado stale.
- `detectar-procesos-repetitivos`: cuando un pipeline de preparación de datos se repita y deba formalizarse.
