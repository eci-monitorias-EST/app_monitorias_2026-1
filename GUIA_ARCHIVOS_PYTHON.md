# 📚 Guía de Archivos Python - App Monitorías 2026-1

> **Contexto del proyecto**: Aplicación Streamlit para recolección de datos pedagógicos, análisis de comentarios con embeddings, visualización 3D y predicción de riesgo crediticio/mora.

---

## 🎯 Índice

1. [Aplicación Principal (Streamlit)](#aplicación-principal-streamlit)
2. [Servicios (Lógica de Negocio)](#servicios-lógica-de-negocio)
3. [Scripts CLI y Utilidades](#scripts-cli-y-utilidades)
4. [Tests](#tests)
5. [Configuración](#configuración)
6. [Componentes y Dominio](#componentes-y-dominio)

---

## 🚀 Aplicación Principal (Streamlit)

### `app/main.py`
**Propósito**: Punto de entrada de la aplicación Streamlit  
**Cuándo usar**: Ejecutar para iniciar la app web  
**Comando**:
```bash
poetry run streamlit run app/main.py
```
**Funcionalidad**: 
- Configura la página Streamlit (título, icono, layout)
- Carga la navegación desde `navigation.py`
- Ejecuta el flujo principal

---

### `app/navigation.py`
**Propósito**: Define las páginas y rutas de navegación  
**Cuándo usar**: Modificar cuando necesites agregar/quitar páginas  
**Funcionalidad**:
- Registra páginas disponibles (actualmente solo `sequential_flow`)
- Define rutas URL y iconos para cada página
- Devuelve objeto de navegación para Streamlit

---

### `app/pages/` - Páginas de la Aplicación

#### `app/pages/sequential_flow.py`
**Propósito**: Página principal del flujo secuencial de ejercicios  
**Cuándo usar**: Renderizar el flujo multi-ejercicio guiado por pasos  
**Funcionalidad**:
- Orquesta el flujo paso a paso por ejercicio
- Gestiona estado de progreso por ejercicio
- Integra validaciones, comentarios 3D y persistencia remota

#### `app/pages/home.py`
**Propósito**: Página de inicio (actualmente no usada en navegación)  
**Cuándo usar**: Si se reactiva una página de bienvenida

#### `app/pages/exercise_1.py`
**Propósito**: Página específica para ejercicio individual (legacy)  
**Cuándo usar**: Referencia para ejercicios individuales

#### `app/pages/data_collection.py`
**Propósito**: Página de recolección de datos (legacy)  
**Cuándo usar**: Si se necesita un módulo de entrada de datos independiente

#### `app/pages/analytics.py`
**Propósito**: Página de análisis y visualizaciones (legacy)  
**Cuándo usar**: Si se reactiva análisis separado del flujo

---

## ⚙️ Servicios (Lógica de Negocio)

### `app/services/remote_sync.py`
**Propósito**: Cliente para sincronización con Google Sheets vía Apps Script  
**Cuándo usar**: Persistir/consultar datos remotos (sesiones, respuestas, comentarios, caches)  
**Clases principales**:
- `RemoteSyncClient`: Cliente base (no-op en versión mock)
- `WebappRemoteSyncClient`: Cliente real que llama al webapp desplegado

**Métodos clave**:
```python
sync_participant()       # Sincronizar participante
sync_feedback()          # Sincronizar feedback
sync_comment_events()    # Sincronizar eventos de comentarios
query_comment_events()   # Consultar comentarios por ejercicio
upsert_embeddings_cache() # Guardar embeddings en cache remoto
query_projection_cache()  # Consultar proyecciones cacheadas
```

---

### `app/services/comment_events.py`
**Propósito**: Gestión de eventos de comentarios individuales  
**Cuándo usar**: Trabajar con comentarios 3D, calcular hashes, normalizar  
**Funciones clave**:
```python
compute_comment_hash(text: str) -> str
build_comment_event(participant_id, exercise, comment_type, text, timestamp) -> dict
```
**Concepto importante**: `comment_hash` identifica únicamente un texto de comentario; el upsert lógico usa `participant_id + exercise + comment_type`

---

### `app/services/embedding_providers.py`
**Propósito**: Generación de embeddings semánticos con sentence-transformers  
**Cuándo usar**: Calcular embeddings para visualización 3D o análisis semántico  
**Clases**:
- `EmbeddingProvider`: Interfaz base
- `MiniLMEmbeddingProvider`: Implementación con `all-MiniLM-L6-v2`

---

### `app/services/modeling.py`
**Propósito**: Modelos ML para proyección 3D (UMAP) y clustering  
**Cuándo usar**: Reducir dimensionalidad de embeddings para visualización  
**Clases**:
- `UMAPProjector`: Proyección 3D incremental con cache
- Soporta ajuste inicial y reutilización de puntos cacheados

---

### `app/services/text_pipeline.py`
**Propósito**: Procesamiento de texto (normalización, limpieza)  
**Cuándo usar**: Normalizar comentarios antes de embeddings  
**Funciones**:
```python
normalize_text(text: str) -> str
```

---

### `app/services/storage.py`
**Propósito**: Persistencia local de datos (sesiones, respuestas, progreso)  
**Cuándo usar**: Guardar/cargar datos en archivos JSON locales  
**Clases**:
- `LocalJsonStorage`: Sistema de persistencia basado en JSON

---

### `app/services/session_service.py`
**Propósito**: Gestión de sesiones de usuario con `access_code` autogenerado  
**Cuándo usar**: Iniciar sesión, recuperar por código, persistir perfil  
**Funcionalidad**:
- Genera códigos de acceso únicos (8 caracteres)
- Persiste `access_code_hash` para seguridad
- Sincroniza con Sheet remoto

---

### `app/services/sequential_flow_state.py`
**Propósito**: Gestión de estado del flujo secuencial multi-ejercicio  
**Cuándo usar**: Controlar pasos, progreso y bloqueos por ejercicio  
**Clases**:
- `SequentialFlowState`: Estado por ejercicio con guards
- Maneja progreso, pasos visitados, bloqueos

---

### `app/services/submission_validation.py`
**Propósito**: Validación de formularios y datos de entrada  
**Cuándo usar**: Validar perfil, feedback, comentarios  
**Funciones**:
```python
validate_profile_data(data: dict) -> tuple[bool, list[str]]
validate_feedback_submission(data: dict) -> tuple[bool, list[str]]
```

---

### `app/services/profile_constraints.py`
**Propósito**: Validación de restricciones de perfil (edad, sexo, grado)  
**Cuándo usar**: Asegurar constraints de datos demográficos  

---

### `app/services/synthetic_imputation.py`
**Propósito**: Generación de datos sintéticos para testing  
**Cuándo usar**: Poblar Sheets con datos de prueba, validar flujo  
**Funcionalidad**:
- Genera perfiles, feedback, comentarios sintéticos
- Marca con `is_test_data=true` y `test_batch_id`

---

### `app/services/data_loader.py`
**Propósito**: Carga de datasets (CSVs, JSONs) para análisis  
**Cuándo usar**: Importar datos de crediticios o históricos  

---

### `app/services/configuration.py`
**Propósito**: Acceso a configuración YAML de la app  
**Cuándo usar**: Cargar config de ejercicios, pasos, validaciones  

---

### `app/services/app_container.py`
**Propósito**: Contenedor de dependencias (DI pattern)  
**Cuándo usar**: Inyectar servicios configurados en páginas  

---

## 🛠️ Scripts CLI y Utilidades

### Scripts de Administración Remota

#### `app_scripts_utils/sheet_snapshot_export.py`
**Propósito**: Exportar snapshots de hojas Google Sheet a JSON/CSV local  
**Cuándo usar**: Inspeccionar, auditar o respaldar contenido del Sheet  
**Comando**:
```bash
poetry run python app_scripts_utils/sheet_snapshot_export.py \
  --sheet respuestas \
  --sheet comment_events \
  --limit-rows 200 \
  --output data/processed/sheet_snapshots
```
**Funcionalidad**:
- Llama a la acción `export_sheet_snapshot` del Apps Script
- Guarda manifest JSON + archivos JSON/CSV por hoja

---

#### `app_scripts_utils/sheet_admin_actions.py`
**Propósito**: Acciones administrativas sobre Google Sheets (reparar, normalizar, borrar)  
**Cuándo usar**: Gestión masiva de datos remotos (legacy, sintéticos, caches)  
**Comando**:
```bash
# Archivar filas legacy
poetry run python app_scripts_utils/sheet_admin_actions.py \
  archive-legacy-rows \
  --source respuestas \
  --archive respuestas_archived \
  --confirm ARCHIVE_LEGACY_ROWS

# Borrar lote sintético
poetry run python app_scripts_utils/sheet_admin_actions.py \
  delete-synthetic-batch \
  --batch-id test-batch-123 \
  --confirm DELETE_SYNTHETIC_BATCH

# Normalizar feedback legacy
poetry run python app_scripts_utils/sheet_admin_actions.py \
  normalize-legacy-feedback \
  --source respuestas \
  --confirm NORMALIZE_LEGACY_FEEDBACK
```

---

#### `app_scripts_utils/synthetic_sheet_imputation.py`
**Propósito**: Sembrar datos sintéticos completos en Google Sheets para validación  
**Cuándo usar**: Poblar Sheet remoto con datos ficticios para testing end-to-end  
**Comando**:
```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py \
  --num-sessions 5 \
  --dataset synthetic_sheet_imputation_dataset.json \
  --generate-html \
  --output-html data/processed/synthetic_3d_viz.html
```
**Funcionalidad**:
- Genera sesiones sintéticas completas (perfil + ejercicios + comentarios)
- Marca con `is_test_data=true` + `test_batch_id`
- Opcionalmente genera visualización 3D HTML

---

#### `app_scripts_utils/webapp_client.py`
**Propósito**: Cliente HTTP reutilizable para comunicarse con Apps Script webapp  
**Cuándo usar**: Base para cualquier script que necesite llamar al webapp  
**Clases**:
- `WebappSyncClient`: Cliente genérico POST con manejo de errores

---

### Scripts de Análisis y Visualización (Legacy - Dispositivos Médicos)

> ⚠️ **Nota**: Estos scripts son del flujo original de dispositivos médicos. Algunos pueden necesitar adaptación para el flujo actual de comentarios pedagógicos.

#### `app_scripts_utils/generar_embeddings.py`
**Propósito**: Generar embeddings semánticos de textos  
**Cuándo usar**: Procesamiento batch de embeddings fuera de Streamlit  

#### `app_scripts_utils/visualizar_3d.py`
**Propósito**: Generar visualización 3D con Plotly  
**Cuándo usar**: Crear visualizaciones 3D independientes  

#### `app_scripts_utils/clustering_bertopic.py`
**Propósito**: Clustering temático con BERTopic  
**Cuándo usar**: Análisis de topics en comentarios  

#### `app_scripts_utils/generar_visualizacion_html.py`
**Propósito**: Exportar visualizaciones 3D a HTML standalone  
**Cuándo usar**: Generar reportes visuales independientes  

#### `app_scripts_utils/crear_base_vectorial.py`
**Propósito**: Construcción de base vectorial de embeddings  
**Cuándo usar**: Preparar índice vectorial para búsqueda semántica  

#### `app_scripts_utils/extraer_dispositivos.py`
**Propósito**: Extracción y preprocesamiento de datos de dispositivos  
**Cuándo usar**: Pipeline inicial de datos legacy  

#### `app_scripts_utils/normalizar_texto.py`
**Propósito**: Normalización batch de textos  
**Cuándo usar**: Limpieza de datasets completos  

#### `app_scripts_utils/generar_informe_clusters.py`
**Propósito**: Generar informe de resultados de clustering  
**Cuándo usar**: Reportes de análisis de clusters  

#### `app_scripts_utils/generar_tabla_conteos.py`
**Propósito**: Tablas resumen de conteos y estadísticas  
**Cuándo usar**: Análisis descriptivo de datos  

#### `app_scripts_utils/clustering_sapbert.py`
**Propósito**: Clustering con SapBERT (embeddings biomédicos)  
**Cuándo usar**: Análisis especializado en dominio médico  

#### `app_scripts_utils/comparar_modelos_embeddings.py`
**Propósito**: Comparación de diferentes modelos de embeddings  
**Cuándo usar**: Benchmarking de calidad de embeddings  

#### `app_scripts_utils/comparar_sapbert_vs_miniLM.py`
**Propósito**: Comparación específica SapBERT vs MiniLM  
**Cuándo usar**: Decidir modelo óptimo para el dominio  

#### `app_scripts_utils/analisis_vecindad_local.py`
**Propósito**: Análisis de vecindad en espacio vectorial  
**Cuándo usar**: Explorar similaridad local entre embeddings  

#### `app_scripts_utils/asignar_nuevos_puntos_conservador.py`
**Propósito**: Asignación conservadora de puntos nuevos a espacio existente  
**Cuándo usar**: Proyección incremental sin re-entrenar modelo  

---

## 🧪 Tests

Todos los tests usan **pytest** y deben ejecutarse con:
```bash
poetry run pytest
poetry run pytest tests/test_<nombre>.py  # Test específico
```

### `tests/conftest.py`
**Propósito**: Fixtures compartidos para todos los tests  
**Fixtures**:
- `tmp_data_dir`: Directorio temporal para tests de I/O
- `mock_remote_sync`: Mock de cliente remoto

### `tests/test_comment_events.py`
**Propósito**: Tests de eventos de comentarios  
**Cubre**: Hashing, construcción de eventos, upsert lógico

### `tests/test_remote_sync.py`
**Propósito**: Tests de sincronización remota  
**Cubre**: Cliente webapp, payloads, caches de embeddings/proyección

### `tests/test_modeling.py`
**Propósito**: Tests de proyección UMAP  
**Cubre**: Proyección 3D, cache, incremental

### `tests/test_text_pipeline.py`
**Propósito**: Tests de normalización de texto  
**Cubre**: Normalización, limpieza, casos edge

### `tests/test_session_service.py`
**Propósito**: Tests de gestión de sesiones  
**Cubre**: Generación de `access_code`, recuperación, persistencia

### `tests/test_sequential_flow_state.py`
**Propósito**: Tests de estado de flujo secuencial  
**Cubre**: Progreso por ejercicio, bloqueos, guards

### `tests/test_storage.py`
**Propósito**: Tests de persistencia local  
**Cubre**: Lectura/escritura JSON, atomicidad

### `tests/test_submission_validation.py`
**Propósito**: Tests de validación de formularios  
**Cubre**: Validación de perfil, feedback, comentarios

### `tests/test_profile_constraints.py`
**Propósito**: Tests de restricciones de perfil  
**Cubre**: Validación de edad, sexo, grado

### `tests/test_synthetic_imputation.py`
**Propósito**: Tests de generación sintética  
**Cubre**: Generación de perfiles, feedback, comentarios de prueba

### `tests/test_sheet_snapshot_export.py`
**Propósito**: Tests de exportación de snapshots  
**Cubre**: CLI, parsing, guardado de archivos

### `tests/test_sheet_admin_actions.py`
**Propósito**: Tests de acciones administrativas  
**Cubre**: CLI, confirmaciones, acciones destructivas

---

## ⚙️ Configuración

### `app/config/settings.py`
**Propósito**: Acceso centralizado a configuración y secretos  
**Cuándo usar**: Obtener URLs, tokens, paths  
**Funciones**:
```python
get_script_url() -> str       # URL del Apps Script webapp
get_form_token() -> str       # Token compartido de seguridad
get_data_dir() -> Path        # Directorio de datos
```

---

## 🧩 Componentes y Dominio

### `app/components/sidebar.py`
**Propósito**: Sidebar reutilizable de Streamlit  
**Cuándo usar**: Mostrar navegación lateral

### `app/components/style.py`
**Propósito**: Estilos CSS y helpers de UI  
**Cuándo usar**: Aplicar estilos consistentes

### `app/domain/models.py`
**Propósito**: Modelos de dominio (dataclasses, tipos)  
**Cuándo usar**: Definir estructuras de datos del negocio  
**Modelos**:
- `ParticipantProfile`
- `ExerciseFeedback`
- `CommentEvent`

---

## 📐 Arquitectura de Dependencias

```
pages/
  ↓ usan
services/
  ↓ usan
domain/ + config/
```

**Regla**: Las páginas NO deben tener lógica de negocio. Todo va en `services/`.

---

## 🔑 Conceptos Clave del Proyecto

### 1. **Fuente de Datos**
- `respuestas`: Fuente consolidada por ejercicio
- `comment_events`: Fuente granular para gráfico 3D (por comentario individual)

### 2. **Identificadores**
- `comment_hash`: Hash SHA256 del texto del comentario (identifica contenido único)
- Clave lógica de upsert: `participant_id + exercise + comment_type`

### 3. **Caches Remotos**
- `embeddings_cache`: Cache idempotente por `comment_hash` + `embedding_version`
- `projection_cache`: Cache idempotente por `comment_hash` + `projection_version`

### 4. **Datos Sintéticos**
- Marcados con `is_test_data = true` + `test_batch_id`
- **NUNCA mezclar con datos reales sin confirmar**

### 5. **Apps Script como API**
- `app_scripts_utils/google_sync_webapp.gs` actúa como backend remoto
- Si cambia, hay que **redeployar** antes de usar acciones nuevas

---

## 🚀 Flujo de Trabajo Típico

### Iniciar la app localmente
```bash
poetry install --with dev
poetry run streamlit run app/main.py
```

### Ejecutar tests
```bash
poetry run pytest
poetry run pytest tests/test_comment_events.py -v
```

### Exportar snapshot del Sheet
```bash
poetry run python app_scripts_utils/sheet_snapshot_export.py \
  --sheet respuestas \
  --sheet comment_events \
  --limit-rows 100
```

### Sembrar datos sintéticos para testing
```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py \
  --num-sessions 3 \
  --generate-html
```

### Limpiar lote sintético después de testing
```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  delete-synthetic-batch \
  --batch-id <tu-batch-id> \
  --confirm DELETE_SYNTHETIC_BATCH
```

---

## 📋 Checklist Antes de PR

1. ✅ `poetry run pytest` pasa todos los tests
2. ✅ No hay datos sintéticos (`is_test_data=true`) en producción
3. ✅ Linting: `poetry run black .`
4. ✅ No hay secretos, tokens o datos sensibles en commits
5. ✅ Screenshots para cambios de UI

---

## 📚 Referencias

- **AGENTS.md**: Guías de skills específicas del proyecto
- **README.md**: Documentación general del proyecto
- **pyproject.toml**: Dependencias y configuración de Poetry
- **Memoria Engram**: Decisiones arquitectónicas y learnings pasados

---

## 💡 Tips

- Usa `logging` en lugar de `print` en servicios
- Mantén las páginas Streamlit **limpias** (solo UI, no lógica)
- **Type hints** son obligatorios en funciones nuevas
- Sigue **PEP 8** para estilo de código
- Nombre de funciones: verbos claros (`load_`, `sync_`, `compute_`)
- Nombre de booleanos: intención clara (`is_valid`, `has_feedback`)

---

**Última actualización**: 2026-04-04  
**Mantenido por**: Equipo ECI Monitorías
