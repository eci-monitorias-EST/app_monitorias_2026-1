---
name: detectar-procesos-repetitivos
description: >
  Detecta cuando una tarea, flujo o patrón se repite lo suficiente como para
  ameritar una skill nueva y obliga a proponerla antes de seguir improvisando.
  Trigger: cuando aparezcan pasos repetitivos, requests parecidos, refactors
  mecánicos o el mismo procedimiento se ejecute varias veces en una sesión.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando el mismo proceso apareció 3 veces o más en una sesión.
- Cuando el usuario pide variaciones mínimas del mismo flujo.
- Cuando hay copy/paste mental: mismos pasos, distinta data.
- Cuando un procedimiento ya tiene reglas claras y reutilizables.

## Critical Patterns

- Si detectás repetición real, frená y decilo explícitamente.
- No sigas resolviendo a mano un patrón reusable sin proponer skill.
- Antes de crear la skill, confirmá que el patrón no sea one-off.
- Si la repetición justifica skill, cargá `skill-creator` y materializala.
- La propuesta debe incluir tradeoff: crear skill ahora vs seguir manual.

## Decision Rules

| Señal | Acción |
| --- | --- |
| Misma secuencia 3+ veces | Proponer skill nueva |
| Mismo checklist con distinta data | Proponer template/skill |
| Refactor o validación mecánica repetida | Proponer skill |
| Caso único o irrepetible | No crear skill |

## Workflow

1. Identificar la repetición concreta.
2. Explicar por qué ya no conviene seguir manualmente.
3. Decirle al usuario que conviene crear una skill reusable.
4. Cargar `skill-creator`.
5. Crear la skill con nombre, trigger, reglas y ejemplos.

## Example

```text
Detecté que ya repetimos varias veces el mismo proceso de inspeccionar flujo,
detectar puntos frágiles, escribir tests focalizados y endurecer contratos.
Esto ya no da para seguir improvisándolo a mano: conviene crear una skill.
Voy a cargar `skill-creator` y te propongo una reusable.
```

## Commands

```bash
# No tiene comandos propios: dispara la creación de skills usando skill-creator.
```

## Resources

- **Related skill**: `skills/detectar-falsos-positivos/SKILL.md`
- **Creator workflow**: cargar `skill-creator` antes de materializar una nueva skill
