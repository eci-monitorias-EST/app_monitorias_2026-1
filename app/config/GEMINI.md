# app/config/AGENTS.md

## Contexto

Configuración de la app, acceso a secrets, variables de entorno y parámetros de comportamiento.

## Responsabilidades

- Centralizar lectura de configuración.
- Resolver secrets y defaults de forma segura.

## Reglas

- No hardcodear tokens ni URLs sensibles fuera de esta capa.
- Validar fallbacks y defaults explícitamente.
- No duplicar configuración entre servicios si puede resolverse acá.

## Skills a usar

- `detectar-falsos-positivos`: cuando una integración remota parezca funcionar pero la configuración sea ambigua, incompleta o contradictoria.
- `detectar-procesos-repetitivos`: cuando la misma configuración o validación se replique en varios módulos.
