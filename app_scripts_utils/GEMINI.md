# app_scripts_utils/AGENTS.md

## Contexto

Scripts utilitarios y exploratorios fuera del runtime principal.

## Responsabilidades

- Experimentación controlada.
- Generación de artifacts o pruebas offline.
- Prototipado técnico antes de integrar al runtime.

## Reglas

- No asumir que un script está listo para producción.
- Si un patrón de script debe entrar a la app, extraer la lógica a `app/services/` en vez de importar el script directamente.
- Documentar claramente qué scripts son exploratorios y cuáles sirven como referencia de integración.

## Skills a usar

- `detectar-procesos-repetitivos`: cuando un script repetido o un procedimiento offline ya amerite una skill o migración al runtime.
- `detectar-falsos-positivos`: cuando un benchmark, clustering o visualización pueda inducir conclusiones engañosas.
- `imputacion-sintetica-sheet-3d`: cuando haya que sembrar datos sintéticos en Google Sheets, generar HTML 3D con MiniLM+UMAP y borrar lotes de prueba por `test_batch_id`.
- `administrar-sheet-remoto`: cuando haya que exportar snapshots, corregir filas legacy, poblar caches o reconstruir proyecciones del Sheet desde CLI.
- `comentarios-3d-incrementales`: cuando haya que auditar, poblar o depurar `comment_events`, `embeddings_cache` y `projection_cache` desde scripts auxiliares.
