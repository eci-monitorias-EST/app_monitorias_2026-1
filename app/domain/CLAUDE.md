# app/domain/AGENTS.md

## Contexto

Modelos de dominio, dataclasses y contratos internos estables de la aplicación.

## Responsabilidades

- Representar entidades del negocio y del flujo.
- Mantener invariantes del dominio y serialización coherente.

## Reglas

- Preferir modelos explícitos sobre diccionarios sueltos cuando la estructura es estable.
- Toda evolución del dominio debe mantener compatibilidad de lectura cuando existan payloads legacy.
- Los estados por ejercicio deben vivir en el dominio, no dispersos en la UI.

## Skills a usar

- `detectar-falsos-positivos`: cuando haya riesgo de interpretar mal estados, clases positivas o resultados serializados.
