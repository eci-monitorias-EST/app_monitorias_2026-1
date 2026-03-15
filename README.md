# 📊 App Monitorías 2026-1

Aplicación desarrollada en **Streamlit** para analítica y visualización de datos del proyecto de monitorías.

Este repositorio sigue buenas prácticas de:

* Arquitectura modular de aplicaciones
* Versionamiento de dependencias con **Poetry**
* Versionamiento de datos con **DVC**
* Flujo colaborativo con Pull Requests

---

# 🗂️ Estructura del proyecto

```
.
│   .dvcignore
│   .gitignore
│   poetry.lock
│   pyproject.toml
│   README.md
│
├── .dvc
│   ├── config
│   ├── cache/
│   └── tmp/
│
├── .github
│   └── pull_request_template.md
│
├── .streamlit
│   └── config.toml
│
├── app
│   │   main.py
│   │   navigation.py
│   │   __init__.py
│   │
│   ├── components
│   │       sidebar.py
│   │       __init__.py
│   │
│   ├── config
│   │       settings.py
│   │       __init__.py
│   │
│   ├── pages
│   │       analytics.py
│   │       home.py
│   │       __init__.py
│   │
│   └── services
│           data_loader.py
│           __init__.py
│
├── data
│   ├── external
│   ├── processed
│   └── raw
│        │   .gitignore
│        │   default_clientes.dvc
│        │   german_credit.dvc
│        │
│        ├── default_clientes
│        │       Default_Clientes.csv
│        │
│        └── german_credit
│                german.data
│                german.data-numeric
│                german.doc
│                Index
│
├── notebooks
└── tests
```

---

# 📦 Archivos raíz

### `.gitignore`

Define archivos y carpetas que no deben subirse a Git.

### `.dvcignore`

Define qué archivos no serán rastreados por DVC.

### `pyproject.toml`

Archivo principal de configuración del proyecto:

* Dependencias
* Configuración de Poetry
* Metadata del proyecto

### `poetry.lock`

Congela versiones exactas de dependencias.

⚠️ Nunca editar manualmente.

---

# 🧠 Carpeta `.dvc`

Contiene configuración interna de **DVC**.

* `cache/` → almacenamiento de versiones de datos
* `tmp/` → locks internos
* `config` → configuración remota o local

⚠️ No modificar manualmente.

---

# 🔁 `.github`

Contiene automatizaciones de GitHub.

### `pull_request_template.md`

Plantilla obligatoria para PR.

Permite:

* estandarizar entregables
* revisar fases (EDA / backend / cluster / etc)

---

# ⚙️ `.streamlit`

### `config.toml`

Configuración global de Streamlit.

Ejemplos:

* puerto
* modo headless
* tema visual

---

# 🧩 Carpeta `app`

Aquí vive toda la aplicación.

## `main.py`

Entry point de Streamlit.

Responsable de:

* inicializar app
* cargar navegación
* renderizar layout base

## `navigation.py`

Define rutas internas y lógica de navegación.

---

## 📁 `components`

Componentes reutilizables UI.

Ej:

* sidebar
* headers
* cards
* layouts

---

## 📁 `config`

Configuraciones internas de la app.

Ej:

* constantes
* variables globales
* rutas

---

## 📁 `pages`

Cada archivo = una página de Streamlit.

Ej:

* `home.py` → landing
* `analytics.py` → dashboards

---

## 📁 `services`

Lógica de negocio y acceso a datos.

Ej:

* loaders
* transformaciones
* conexión a APIs

---

# 💾 Carpeta `data`

Versionada con **DVC**.

## `raw`

Datos originales.

Nunca modificarlos manualmente.

Cada dataset tiene:

* carpeta física
* archivo `.dvc` tracker

## `processed`

Datos transformados.

Salida de pipelines.

## `external`

Datos externos descargados o mock.

---

# 📓 `notebooks`

Exploración:

* EDA
* pruebas de modelos
* experimentación

⚠️ No lógica productiva aquí.

---

# 🧪 `tests`

Tests unitarios:

* services
* loaders
* lógica analítica

---

# 🚀 Ejecutar localmente

```bash
poetry install
poetry run streamlit run app/main.py
```

---

# 🌎 Deploy

Deploy automático desde GitHub a Streamlit Cloud.

Cada push a `main` puede gatillar rebuild.

---

# 📊 DVC

Traer datos:

```bash
dvc pull
```

Agregar datos nuevos:

```bash
dvc add data/raw/nuevo_dataset
```

---

✅ Proyecto listo para trabajo colaborativo profesional.
