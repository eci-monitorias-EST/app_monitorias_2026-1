# 📊 EDA — app_monitorias_2026-1

Este módulo contiene el análisis exploratorio de datos (EDA) del proyecto de monitorías.

Aquí se trabaja principalmente con:

* Python
* Poetry
* Jupyter Notebooks
* DVC (versionado de datasets)

---

## 📁 Estructura del directorio

```
.
├── .dvc
├── .github
├── data
│   ├── processed
│   └── raw
├── notebooks
└── src
```

### 🔵 `.dvc/`

Directorio interno gestionado automáticamente por **DVC (Data Version Control)**.

Contiene información necesaria para el versionamiento de datasets y artefactos pesados.

* **cache/** → almacena los archivos reales versionados por DVC usando hashes (MD5)
* **tmp/** → archivos temporales usados por DVC

⚠️ No debe modificarse manualmente.

---

### 🟣 `.github/`

Configuraciones del repositorio como:

* workflows de CI/CD
* plantillas
* automatizaciones

---

### 🟢 `data/`

Directorio donde viven los datasets del proyecto.

#### 📥 `data/raw/`

Datasets originales sin transformar.

Los archivos pesados **NO se suben a Git**, se versionan con DVC mediante archivos `.dvc`.

#### ⚙️ `data/processed/`

Datasets ya limpiados o transformados para análisis o modelamiento.

---

### 📒 `notebooks/`

Contiene notebooks de análisis exploratorio:

* análisis descriptivo
* visualizaciones
* hipótesis
* exploración de calidad de datos

---

### 🧠 `src/`

Código reutilizable del proyecto:

* funciones de limpieza
* feature engineering
* loaders
* utilidades

Este código puede ser usado luego por pipelines o aplicaciones.

---

## 🚀 Instalación del entorno

### 1️⃣ Instalar Poetry (si no lo tienes)

```bash
pip install poetry
```

Verificar:

```bash
poetry --version
```

---

### 2️⃣ Instalar dependencias

```bash
poetry install
```

---

## 📓 Uso con Notebooks

### Instalar ipykernel

```bash
poetry add --group dev ipykernel
```

### Registrar kernel

```bash
poetry run python -m ipykernel install --user --name monitorias-eda
```

Luego seleccionar ese kernel dentro del notebook.

---

## 📂 Versionado de datasets

Ejemplo:

```bash
dvc add data/raw/Default_Clientes.csv
git add .
git commit -m "feat(EDA): track dataset with dvc"
```

---

## ⚠️ Importante

Siempre ejecutar scripts dentro del entorno poetry:

```bash
poetry run python script.py
```
