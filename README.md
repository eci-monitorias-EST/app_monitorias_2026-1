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

---

### 🔵 `.dvc/`

Directorio interno gestionado automáticamente por **DVC (Data Version Control)**.

Contiene información necesaria para el versionamiento de datasets y artefactos pesados.

* **cache/** → almacena los archivos reales versionados por DVC usando hashes (MD5)
* **tmp/** → archivos temporales usados por DVC
* **config** → configuración de remotos o comportamiento de DVC

⚠️ No debe modificarse manualmente.

---

### 🟣 `.github/`

Configuraciones del repositorio como:

* workflows de CI/CD
* plantillas de Pull Request
* automatizaciones

---

### 🟢 `data/`

Directorio donde viven los datasets del proyecto.

#### 📥 `data/raw/`

Datasets originales sin transformar.

Los archivos pesados **NO se suben a Git**, se versionan con DVC mediante archivos `.dvc`.

Cada dataset debe tener:

* una carpeta física con los archivos
* un archivo `.dvc` tracker generado con `dvc add`

#### ⚙️ `data/processed/`

Datasets ya limpiados o transformados para análisis o modelamiento.

Generalmente son salida de pipelines o notebooks.

---

### 📒 `notebooks/`

Contiene notebooks de análisis exploratorio:

* análisis descriptivo
* visualizaciones
* hipótesis
* exploración de calidad de datos
* validación de supuestos

⚠️ La lógica productiva no debe quedarse aquí. Debe migrarse luego a `src/` o a la app.

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

## 📂 Versionado de datasets con DVC

Ejemplo:

```bash
dvc add data/raw/default_clientes
```

Luego:

```bash
git add .
git commit -m "feat(EDA): track dataset with dvc"
```

---

## 🔀 Uso de DVC con múltiples ramas (EDA / modeling / app)

Cuando el proyecto utiliza **DVC para versionar datasets**, es importante entender cómo funciona el cambio de ramas.

Git controla:

* código
* notebooks
* archivos `.dvc`

DVC controla:

* los archivos de datos reales

Esto significa que:

👉 Al cambiar de rama con `git checkout`, **los datasets físicos no cambian automáticamente.**

Por ejemplo:

* La rama `EDA` puede tener datasets en `data/raw/`
* La rama `app` puede no tenerlos
* Sin embargo, al cambiar de rama, los folders pueden seguir existiendo localmente

Esto ocurre porque Git no versiona los archivos pesados ignorados por `.gitignore`.

---

### ✅ Sincronizar datasets después de cambiar de rama

Siempre que cambies de rama en un proyecto con DVC debes ejecutar:

```bash
poetry run dvc checkout
```

Este comando:

* compara los archivos `.dvc` de la rama actual
* sincroniza los archivos físicos del workspace
* elimina datasets que no pertenecen a la rama
* restaura datasets que sí pertenecen a la rama

---

### 🧠 Flujo recomendado profesional

1️⃣ Cambiar de rama

```bash
git checkout EDA
```

2️⃣ Sincronizar datasets

```bash
poetry run dvc checkout
```

3️⃣ (Opcional) traer datos desde remoto

```bash
poetry run dvc pull
```

---

### 🚨 Regla importante

Nunca asumir que los datasets visibles en disco corresponden a la rama actual.

Siempre usar `dvc checkout` para garantizar consistencia.

---

## ⚠️ Importante

Siempre ejecutar scripts dentro del entorno poetry:

```bash
poetry run python script.py
```

---

✅ Este módulo está preparado para exploración profesional reproducible y trabajo colaborativo con control de versiones de código y datos.
