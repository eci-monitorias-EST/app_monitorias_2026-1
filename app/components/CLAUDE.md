# app/components/AGENTS.md

## Contexto

Componentes reutilizables de UI y helpers visuales para Streamlit.

## Responsabilidades

- Encapsular presentación reutilizable.
- Evitar duplicación de estilos y widgets compartidos.

## Reglas

- No mover lógica de negocio a esta carpeta.
- Mantener interfaces simples y orientadas a render.
- Si un componente necesita datos procesados, recibirlos ya listos desde servicios o páginas.

## Skills a usar

- `detectar-procesos-repetitivos`: cuando aparezca repetición de layout, estilos o widgets que convenga formalizar.
