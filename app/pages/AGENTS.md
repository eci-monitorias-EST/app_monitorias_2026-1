# app/pages/AGENTS.md

## Contexto

Páginas Streamlit y orquestación del flujo visible al usuario.

## Responsabilidades

- Renderizar el flujo secuencial.
- Coordinar interacción del usuario con servicios.
- Mostrar mensajes de error seguros para usuario.

## Reglas

- Mantener la UI delgada; mover validación, estado y persistencia a `app/services/`.
- No decidir lógica de negocio directamente en la página si puede vivir en servicios.
- Cuando un paso dependa de guards, centralizarlos en la máquina de estados o en servicios dedicados.

## Skills a usar

- `detectar-falsos-positivos`: al mostrar resultados de modelos, sync remoto o visualizaciones que puedan inducir a una lectura errónea.
- `detectar-procesos-repetitivos`: si se repiten patrones de formularios, guards o navegación que ameriten abstraerse.
