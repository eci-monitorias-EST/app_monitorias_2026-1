# app/AGENTS.md

## Contexto

Esta carpeta contiene el runtime principal de la aplicación Streamlit.

## Responsabilidades

- Componer la UI, navegación, servicios, dominio y configuración.
- Mantener una separación clara entre páginas, servicios y modelos.

## Reglas

- No mezclar lógica de negocio pesada en `main.py` ni `navigation.py`.
- Mantener la dirección de dependencias: `pages -> services -> domain/config`.
- Si una regla es específica de una subcarpeta, priorizar el `AGENTS.md` más interno.

## Skills a usar

- `detectar-procesos-repetitivos`: cuando una secuencia de cambios o validaciones se repita y convenga convertirla en skill reusable.
- `detectar-falsos-positivos`: cuando un flujo, clasificación o sincronización parezca exitosa pero tenga señales ambiguas o contradictorias.
