# Bankify Monitorias

Aplicación educativa desarrollada en `Streamlit` para acompañar ejercicios de Ingeniería Estadística dentro de un contexto bancario. La narrativa usa el universo de Bankify como hilo conductor: el área de Ingeniería Estadística ayuda a decidir si una solicitud de crédito se aprueba y a estimar la probabilidad de mora, mientras el estudiante explora datos, modelos, explicaciones y retroalimentación.

El repositorio está organizado con principios de programación orientada a objetos, alta cohesión y bajo acoplamiento. La interfaz vive en `app/pages`, la composición de navegación en `app/navigation.py`, la configuración en `app/config`, y la lógica reutilizable en `app/services`.

## Arquitectura

La decisión técnica principal es mantener `Streamlit` como frontend único y concentrar la lógica de negocio en servicios internos de Python. Esto evita duplicar contratos entre una SPA y una API separada, mantiene el flujo secuencial fácil de demostrar en clase y facilita el despliegue.

Capas esperadas:

- Presentación: páginas de `Streamlit`, componentes visuales y navegación.
- Servicios de aplicación: sesión, persistencia, limpieza de texto, embeddings, reducción dimensional, explicabilidad y predicción.
- Persistencia: Google Sheets vía Apps Script como integración principal o alternativa equivalente con contrato idempotente.
- Datos: datasets versionados con `DVC`.
- Documentación y pruebas: README, notebooks y suite `pytest`.

## Estructura Del Repositorio

```text
.
├── app
│   ├── main.py
│   ├── navigation.py
│   ├── components/
│   ├── config/
│   ├── pages/
│   └── services/
├── data
│   └── raw/
├── notebooks/
├── apps_script_completo.txt
├── pyproject.toml
├── poetry.lock
└── README.md
```

### Módulos Principales

- `app/main.py`: punto de entrada de la app `Streamlit`.
- `app/navigation.py`: define la navegación y las páginas disponibles.
- `app/pages/home.py`: entrada visual y contexto narrativo.
- `app/pages/data_collection.py`: captura de sesión y datos del participante.
- `app/pages/exercise_1.py`: flujo de ejercicio individual con persistencia idempotente.
- `app/pages/analytics.py`: espacio para dashboards y exploración.
- `app/pages/sequential_flow.py`: orquestador del flujo secuencial actual.
- `app/components/`: piezas visuales reutilizables.
- `app/config/settings.py`: lectura de secretos y parámetros de conexión.
- `app/services/data_loader.py`: carga de datasets y utilidades de acceso a datos.
- `app_scripts_utils/synthetic_sheet_imputation.py`: flujo batch para sembrar datos sintéticos, renderizar HTML 3D y borrar lotes de prueba por `test_batch_id`.
- `app_scripts_utils/sheet_snapshot_export.py`: exporta snapshots controlados de hojas remotas para auditoría local.
- `app_scripts_utils/sheet_admin_actions.py`: CLI para normalizar legacy, poblar caches y operar mantenimiento remoto del Sheet.
- `apps_script_completo.txt`: versión en texto del Apps Script que actúa como integración con Google Sheets.

## Flujo Funcional

La experiencia prevista para el estudiante es:

1. Bienvenida con contexto del caso Bankify.
2. Registro o recuperación de sesión sin duplicar participantes.
3. Elección del ejercicio: aprobación de crédito o probabilidad de mora.
4. Conocimiento del dataset y descripción de variables.
5. Exploración con gráficos y espacios de interpretación.
6. Predicción del modelo con explicaciones locales y globales.
7. Visualización 3D anónima de comentarios por ejercicio.
8. Retroalimentación final con escala Likert y campos condicionales.

## Persistencia Y Sesiones

La regla de negocio es simple: un usuario conserva un único registro de sesión y cada respuesta debe comportarse como `upsert`, no como inserción duplicada.

Supuestos adoptados:

- La identidad operativa del usuario es el `session_id` devuelto o recuperado por la capa de persistencia.
- Para retomar sesión sin duplicados, el usuario ingresa un identificador estable de acceso, por ejemplo correo institucional o código académico.
- Si el usuario recarga o pierde conexión, la misma sesión debe poder retomar el flujo sin perder avances.
- Las respuestas por ejercicio se actualizan sobre el mismo registro.
- La retroalimentación final también debe ser única por sesión.
- Los comentarios anónimos para visualización 3D se agregan por ejercicio y se procesan en lote cuando el usuario completa la actividad.

### Legacy: qué significa en este proyecto

En este repositorio llamamos `legacy` a filas viejas escritas con contratos anteriores del Apps Script o de la app, antes de que el esquema actual se estabilizara.

Ejemplos de síntomas legacy detectados en snapshots reales:

- columnas corridas, donde `is_test_data` contiene un timestamp o `updated_at` queda vacío;
- feedback con `exercise` numérico y `rating` textual;
- registros de control donde `exercise` quedó como `completed` en vez de tener una columna `status` coherente;
- comentarios parciales guardados como varias filas separadas cuando hoy el flujo prefiere respuestas consolidadas.

El objetivo de las acciones administrativas no es “tocar por tocar”, sino:

- identificar filas legacy,
- corregirlas o archivarlas con criterio,
- y evitar que contaminen caches nuevas como `embeddings_cache` y `projection_cache`.

Contrato recomendado para la hoja o backend:

- `sesiones`: un registro por participante/sesión.
- `respuestas`: respuestas estructuradas por ejercicio.
- `historial_comentarios`: auditoría/histórico de comentarios de texto.
- `feedback`: retroalimentación final.
- `control_ingreso`: registro de control para evitar duplicados y facilitar recuperación.
- `embeddings_cache`: cache de embeddings por `participant_id + exercise + comment_hash`.
- `projection_cache`: cache de coordenadas 3D por `participant_id + exercise + comment_hash`.

### Estrategia actual recomendada para Streamlit Community Cloud

Dado que la app se desplegará en Streamlit Community Cloud, el filesystem local de la app no debe tratarse como fuente principal de verdad para datos de usuarios. La estrategia recomendada es:

1. `st.session_state` para datos transitorios de la sesión actual.
2. Google Sheets + Apps Script como persistencia remota principal gratuita.
3. Escrituras **consolidadas**, no una llamada remota por cada campo.
4. `upsert` idempotente por `participant_id + exercise`.
5. batching/chunks para operaciones masivas o reprocesos.
6. retry/backoff para lecturas/escrituras remotas.
7. caches remotos (`embeddings_cache`, `projection_cache`) y caches locales (`st.cache_data`, `st.cache_resource`) para evitar recomputaciones costosas.

## Visualización 3D y caches

Para que el gráfico 3D sea rápido y siga siendo gratis en Streamlit Cloud, el flujo recomendado es:

1. Guardar una respuesta consolidada por ejercicio.
2. Generar `comment_hash` del comentario combinado.
3. Revisar `embeddings_cache`:
   - si el hash ya existe, reutilizar el embedding;
   - si no, calcular MiniLM y guardar el vector.
4. Revisar `projection_cache`:
   - si ya existe la proyección para ese hash, reutilizarla;
   - si no, proyectar y guardar.
5. Resaltar en el gráfico al usuario actual comparando `participant_id` del punto con el `participant_id` de la sesión activa.

### Hojas auxiliares sugeridas

#### `embeddings_cache`

- `participant_id`
- `exercise`
- `comment_hash`
- `clean_comment`
- `embedding_model`
- `embedding_vector_json`
- `updated_at`

#### `projection_cache`

- `participant_id`
- `public_alias`
- `exercise`
- `comment_hash`
- `x`
- `y`
- `z`
- `projection_version`
- `reducer_provider`
- `updated_at`

## Configuración

La capa de configuración debe separar secretos de parámetros no sensibles.

Valores esperados:

- `google_script_url`: URL del Web App de Apps Script.
- `google_script_token`: token de autenticación ligera para evitar llamadas no autorizadas.
- `APP_TIMEOUT_SECONDS`: tiempo de espera para llamadas remotas.
- `APP_CONFIG_YAML`: ruta al YAML de configuración no sensible, si se usa.

`app/config/settings.py` ya centraliza la lectura de secretos desde `Streamlit secrets`. En producción, los secretos deben vivir fuera del repositorio y nunca hardcodearse en el código.

Ejemplo recomendado de `.env.example`:

```bash
GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/...
GOOGLE_SCRIPT_TOKEN=replace_me
APP_TIMEOUT_SECONDS=10
APP_CONFIG_YAML=config/app.yaml
```

## Datos

### `Default_Clientes.csv`

Dataset para el ejercicio de probabilidad de mora. Se conserva versionado con `DVC` dentro de `data/raw`.

### Statlog German Credit Data

Para el ejercicio de aprobación de crédito se debe usar la fuente oficial de UCI:

- Dataset: Statlog (German Credit Data)
- URL oficial: https://archive.ics.uci.edu/dataset/144/statlog%2Bgerman%2Bcredit%2Bdata
- DOI: `10.24432/C5NC77`

La documentación oficial de UCI indica que el dataset contiene 1000 instancias, 20 atributos y dos formatos de archivo: `german.data` y `german.data-numeric`. La app debe usar la definición oficial de variables y mapearla explícitamente en el código y en el README.

En este repositorio, la implementación productiva carga la tabla oficial desde [data/raw/statlog+german+credit+data/german.data](/d:/Estudios/Universidad/Ingenieria_estadistica/10.Decimo_Semestr_Local/Monitorias/data/raw/statlog+german+credit+data/german.data) y conserva [data/raw/statlog+german+credit+data/german.data-numeric](/d:/Estudios/Universidad/Ingenieria_estadistica/10.Decimo_Semestr_Local/Monitorias/data/raw/statlog+german+credit+data/german.data-numeric) como referencia técnica adicional. Si se cambia la carpeta, debe actualizarse el loader.

### Mapeo Oficial De Atributos

Resumen de los 20 atributos oficiales usados por la app:

| # | Atributo oficial | Descripción operativa en la app |
|---|---|---|
| 1 | Status of existing checking account | Estado de la cuenta corriente del solicitante |
| 2 | Duration in month | Duración del crédito en meses |
| 3 | Credit history | Historial crediticio |
| 4 | Purpose | Propósito del crédito |
| 5 | Credit amount | Monto solicitado |
| 6 | Savings account/bonds | Ahorros o bonos |
| 7 | Present employment since | Antigüedad laboral |
| 8 | Installment rate in percentage of disposable income | Cuota como porcentaje del ingreso disponible |
| 9 | Personal status and sex | Estado personal y sexo |
| 10 | Other debtors / guarantors | Otros deudores o codeudores |
| 11 | Present residence since | Antigüedad en la residencia actual |
| 12 | Property | Tipo de propiedad |
| 13 | Age in years | Edad |
| 14 | Other installment plans | Otros planes de pago |
| 15 | Housing | Tipo de vivienda |
| 16 | Number of existing credits at this bank | Número de créditos vigentes en el banco |
| 17 | Job | Tipo de trabajo |
| 18 | Number of people being liable to provide maintenance for | Número de dependientes |
| 19 | Telephone | Disponibilidad de teléfono |
| 20 | Foreign worker | Condición de trabajador extranjero |

La codificación original de categorías `A11`, `A12`, etc. debe mantenerse como referencia técnica en el código de datos. La app puede traducirlas a lenguaje pedagógico para el estudiante, pero sin inventar atributos nuevos.

## Apps Script

`apps_script_completo.txt` debe tratarse como código fuente auxiliar. Su función es recibir escrituras idempotentes desde la app y sincronizarlas con Google Sheets.

Requisitos del contrato:

- Autenticación ligera con token.
- Idempotencia por `session_id` + `ejercicio`.
- Actualización de filas existentes en vez de inserciones duplicadas.
- Respuesta JSON consistente para que `Streamlit` pueda rehidratar sesión.

Si Apps Script se convierte en cuello de botella, la mitigación recomendada es:

- agrupar escrituras por lote,
- cachear lecturas frecuentes,
- usar una hoja de control de sesiones,
- y mantener una capa de persistencia intermedia con `upsert`.

## Herramientas administrativas del Sheet

El proyecto incluye CLIs para inspeccionar y administrar el contenido remoto del Google Sheet sin depender de la UI de Google Sheets.

### Exportar snapshots de hojas

```bash
poetry run python app_scripts_utils/sheet_snapshot_export.py \
  --sheet sesiones \
  --sheet respuestas \
  --sheet historial_comentarios \
  --sheet feedback \
  --sheet control_ingreso \
  --sheet embeddings_cache \
  --sheet projection_cache \
  --limit-rows 20 \
  --snapshot-label current-sheet-audit
```

Esto exporta JSON/CSV locales para auditoría y genera un manifest reutilizable.

### Acciones administrativas remotas

#### `fix-legacy-rows`

Sirve para corregir filas detectadas como legacy a partir de un snapshot exportado.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  fix-legacy-rows \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json
```

Con `--execute` aplica cambios reales.

#### `normalize-feedback-schema`

Sirve para normalizar filas de `feedback` que quedaron con columnas corridas o contratos viejos.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  normalize-feedback-schema \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json \
  --exercise credit_approval
```

#### `archive-legacy-rows`

Sirve para mover o marcar filas legacy con una razón explícita, evitando que sigan contaminando lectura/caches.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  archive-legacy-rows \
  --snapshot data/processed/sheet_snapshots/current-sheet-audit-manifest.json \
  --archive-reason legacy_snapshot_cleanup \
  --execute \
  --confirm-phrase ARCHIVE_LEGACY_ROWS
```

#### `clear-sheet-rows`

Sirve para limpiar filas específicas de una hoja auxiliar, por ejemplo `projection_cache` para una versión de proyección.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  clear-sheet-rows \
  --sheet projection_cache \
  --exercise credit_approval \
  --projection-version projection-v3 \
  --execute \
  --confirm-phrase CLEAR_SHEET_ROWS
```

#### `backfill-embeddings-cache`

Sirve para poblar `embeddings_cache` con embeddings ya calculados a partir de un archivo intermedio de filas preparadas.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  backfill-embeddings-cache \
  --rows-file tmp/embeddings_rows.json \
  --exercise credit_approval \
  --embedding-version emb-v1 \
  --embedding-provider minilm \
  --execute
```

#### `rebuild-projection-cache`

Sirve para reconstruir `projection_cache` desde un archivo con puntos ya proyectados.

```bash
poetry run python app_scripts_utils/sheet_admin_actions.py \
  rebuild-projection-cache \
  --rows-file tmp/projection_rows.json \
  --exercise credit_approval \
  --projection-version projection-v3 \
  --embedding-provider minilm \
  --reduction-provider umap \
  --execute \
  --confirm-phrase REBUILD_PROJECTION_CACHE
```

## Flujo sintético de prueba a gran escala

Para sembrar datos sintéticos, generar HTML 3D y luego borrarlos por lote:

```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py \
  --minimum-records 100 \
  seed \
  --test-batch-id demo-lote-100 \
  --chunk-size 20
```

Render HTML 3D por ejercicio:

```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py render --test-batch-id demo-lote-100 --exercise default_risk
poetry run python app_scripts_utils/synthetic_sheet_imputation.py render --test-batch-id demo-lote-100 --exercise credit_approval
```

Simulación de borrado:

```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py --timeout 120 delete-dry-run --test-batch-id demo-lote-100
```

Borrado real (solo con confirmación explícita):

```bash
poetry run python app_scripts_utils/synthetic_sheet_imputation.py \
  --timeout 120 \
  delete \
  --test-batch-id demo-lote-100 \
  --execute \
  --verify-attempts 6 \
  --verify-backoff-seconds 2
```

## Ejecución Local

```bash
poetry install
poetry run streamlit run app/main.py
```

## Docker

La aplicación está pensada para ser contenedorizable. Si el repositorio incorpora `Dockerfile` y, opcionalmente, `docker-compose.yml`, el flujo recomendado es:

```bash
docker build -t bankify-monitorias .
docker run --rm -p 8501:8501 --env-file .env bankify-monitorias
```

## Pruebas

```bash
poetry run pytest
```

Las pruebas deben cubrir, como mínimo:

- recuperación de sesión sin duplicados,
- contrato de persistencia e idempotencia,
- limpieza y preparación de comentarios,
- embeddings y reducción a 3D,
- predicción y explicabilidad,
- render mínimo del flujo principal.

## DVC

```bash
dvc pull
```

Usar `DVC` para los datasets evita que los archivos grandes queden copiados manualmente en Git. Los datos crudos no deben editarse a mano; si cambian, debe quedar trazabilidad en el pipeline.

## Supuestos De Negocio

- `Streamlit` es la interfaz principal y no se introduce un frontend adicional salvo que el repo lo requiera más adelante.
- La persistencia de verdad vive en la integración externa o en la capa que la reemplace, no en `st.session_state`.
- La identidad del usuario es anónima para la visualización de comentarios; solo se resalta la sesión actual.
- La explicación pedagógica del modelo se genera a partir de salidas textuales de LIME/SHAP y se resume para estudiantes.
- Para la descripción de German Credit no se inventan variables: se usa la documentación oficial de UCI.

## Referencias

- UCI Machine Learning Repository: Statlog (German Credit Data)
- Streamlit: https://streamlit.io/
- DVC: https://dvc.org/
