# tests/AGENTS.md

## Contexto

Suite `pytest` del proyecto.

## Responsabilidades

- Verificar comportamiento observable.
- Cubrir cambios de lógica, validación, sync y flujo.

## Reglas

- Priorizar tests unitarios y focalizados.
- Cubrir tanto caminos felices como errores y ambigüedades.
- Evitar dependencias de red real salvo pruebas explícitas y controladas fuera de esta carpeta.
- Cuando una regresión aparezca en flujo o sync, agregar test antes o junto con la corrección.

## Skills a usar

- `detectar-falsos-positivos`: para diseñar tests que distingan éxito real vs éxito aparente.
- `detectar-procesos-repetitivos`: cuando una familia de tests repetidos merezca fixture, helper o skill reusable.
