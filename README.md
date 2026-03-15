# App Monitorías 2026-1

Este repositorio contiene la estructura base de una aplicación desarrollada con **Streamlit**.

La idea de esta organización es separar responsabilidades para que el proyecto sea más fácil de mantener, escalar y desplegar.

## Estructura del proyecto

```text
.
|   .gitignore
|   poetry.lock
|   pyproject.toml
|   README.md
|   
+---.github
|       pull_request_template.md
|       
+---.streamlit
|       config.toml
|
+---app
|   |   main.py
|   |   navigation.py
|   |   __init__.py
|   |
|   +---components
|   |       sidebar.py
|   |       __init__.py
|   |
|   +---config
|   |       settings.py
|   |       __init__.py
|   |
|   +---pages
|   |       analytics.py
|   |       home.py
|   |       __init__.py
|   |
|   \---services
|           data_loader.py
|           __init__.py
|
+---data
+---notebooks
\---tests
```

---

## Qué va en cada archivo y carpeta

### `.gitignore`

Archivo que indica qué elementos **no deben subirse al repositorio**.

Aquí normalmente se ignoran:

* archivos temporales,
* cachés de Python,
* entornos virtuales,
* secretos,
* archivos generados automáticamente.

Ejemplos típicos:

* `__pycache__/`
* `*.pyc`
* `.venv/`
* `.env`

---

### `poetry.lock`

Archivo generado por **Poetry**.

Poetry es la herramienta que se está usando para administrar dependencias del proyecto.

Este archivo guarda las **versiones exactas** de las librerías instaladas para que el proyecto se pueda reproducir igual en otros equipos o en despliegue.

No se debe editar manualmente.

---

### `pyproject.toml`

Archivo principal de configuración del proyecto Python.

Aquí se define:

* el nombre del proyecto,
* la versión,
* la versión mínima de Python,
* las dependencias,
* configuraciones de Poetry.

En este proyecto sirve principalmente para que Poetry gestione las librerías necesarias para ejecutar la aplicación.

---

### `README.md`

Documento principal del repositorio.

Debe explicar:

* qué hace el proyecto,
* cómo está organizado,
* cómo ejecutarlo localmente,
* cómo desplegarlo,
* convenciones de trabajo del equipo.

---

## Carpeta `.github/`

Carpeta especial de GitHub.

Contiene configuraciones relacionadas con el flujo de trabajo en el repositorio.

### `.github/pull_request_template.md`

Plantilla que aparece automáticamente al abrir un **Pull Request**.

Un **Pull Request** es una solicitud para fusionar cambios de una rama a otra.

Este archivo ayuda a que todos documenten sus cambios de forma consistente.

Aquí normalmente se describe:

* qué se cambió,
* por qué se cambió,
* cómo probarlo,
* consideraciones adicionales.

---

## Carpeta `.streamlit/`

Carpeta especial de configuración de Streamlit.

### `.streamlit/config.toml`

Archivo de configuración de la app.

Aquí se pueden definir aspectos como:

* tema visual,
* color principal,
* comportamiento del servidor,
* otras opciones propias de Streamlit.

Es útil para mantener una configuración uniforme entre desarrollo local y despliegue.

---

## Carpeta `app/`

Esta es la carpeta principal de la aplicación.

Aquí vive el código fuente de la app Streamlit.

---

### `app/main.py`

Es el **punto de entrada** de la aplicación.

Esto significa que es el archivo principal que Streamlit ejecuta para iniciar la app.

Actualmente se corre con un comando como:

```bash
poetry run streamlit run app/main.py
```

En este archivo normalmente debe ir:

* la configuración general de la app,
* el título o configuración inicial,
* el arranque de la navegación,
* el montaje general de la aplicación.

Debe mantenerse lo más limpio posible.

La lógica de negocio no debería concentrarse aquí.

---

### `app/navigation.py`

Archivo encargado de la **navegación** de la app.

La navegación es el mecanismo que decide:

* qué páginas existen,
* en qué orden aparecen,
* cuál es la página principal,
* cómo se mueve el usuario entre secciones.

Aquí se define la estructura de páginas de Streamlit.

Esto permite que `main.py` no tenga toda la lógica mezclada.

---

### `app/__init__.py`

Archivo que indica que `app/` debe tratarse como un paquete de Python.

En proyectos pequeños puede estar vacío, y eso está bien.

Su existencia ayuda a que Python reconozca mejor la estructura del proyecto.

---

## Carpeta `app/components/`

Aquí van los **componentes reutilizables** de la interfaz.

Un componente es una pieza de la interfaz que puede usarse en varias páginas.

Ejemplos:

* barras laterales,
* encabezados,
* tarjetas,
* filtros,
* bloques visuales repetidos.

La idea es evitar repetir el mismo código visual en varios archivos.

### `app/components/sidebar.py`

Archivo para definir la barra lateral de la aplicación.

La **sidebar** es el panel lateral izquierdo que normalmente contiene:

* navegación,
* filtros,
* accesos rápidos,
* información de contexto.

Si en el futuro la app necesita una barra lateral más robusta, este archivo será el lugar correcto para implementarla.

### `app/components/__init__.py`

Marca la carpeta de componentes como paquete Python.

---

## Carpeta `app/config/`

Aquí va la configuración interna de la aplicación.

Se usa para centralizar valores que no conviene escribir repetidamente en distintos archivos.

Ejemplos:

* nombres de variables,
* rutas,
* constantes,
* parámetros globales,
* textos reutilizables,
* configuración de entorno.

### `app/config/settings.py`

Archivo pensado para almacenar configuraciones del sistema.

Aquí podrían ir, por ejemplo:

* nombre de la app,
* rutas base,
* configuraciones de carga,
* parámetros de entorno,
* constantes reutilizadas en distintas partes.

Centralizar esta información reduce errores y facilita cambios futuros.

### `app/config/__init__.py`

Marca esta carpeta como paquete Python.

---

## Carpeta `app/pages/`

Aquí se almacenan las **páginas** de la aplicación.

Cada archivo representa una sección visible de la app.

Ejemplos actuales:

* Inicio
* Analítica

La ventaja de esta separación es que cada página puede crecer sin volver inmanejable el archivo principal.

### `app/pages/home.py`

Página de inicio de la aplicación.

Aquí normalmente debe ir:

* bienvenida,
* introducción al sistema,
* explicación general,
* accesos a otras secciones,
* contexto funcional del proyecto.

### `app/pages/analytics.py`

Página para la sección analítica.

Aquí debería ir toda la parte relacionada con:

* visualización de datos,
* análisis,
* indicadores,
* tablas,
* gráficas,
* resultados de procesamiento.

### `app/pages/__init__.py`

Marca la carpeta de páginas como paquete Python.

---

## Carpeta `app/services/`

Aquí debe ir la **lógica de negocio o de aplicación**.

Esto significa el código que hace trabajo útil detrás de la interfaz.

Ejemplos:

* cargar datos,
* transformar información,
* hacer cálculos,
* llamar procesos,
* preparar resultados para mostrar en pantalla.

La regla importante es:

* la interfaz muestra cosas,
* los servicios hacen trabajo.

### `app/services/data_loader.py`

Archivo pensado para la carga de datos.

Aquí debería concentrarse la lógica para:

* leer archivos,
* cargar CSV o Excel,
* validar estructura de datos,
* preparar insumos para las páginas.

Esto evita que cada página cargue datos por su cuenta y repita lógica.

### `app/services/__init__.py`

Marca esta carpeta como paquete Python.

---

## Carpeta `data/`

Aquí deben almacenarse los datos que usa el proyecto.

Dependiendo del crecimiento de la app, más adelante puede subdividirse en carpetas como:

* `raw/` para datos originales,
* `processed/` para datos procesados,
* `external/` para datos externos.

Por ahora funciona como contenedor general.

---

## Carpeta `notebooks/`

Aquí van los notebooks de exploración o análisis.

Un **notebook** es un archivo interactivo, por ejemplo `.ipynb`, que permite mezclar:

* código,
* texto,
* tablas,
* gráficos.

Esta carpeta es ideal para:

* pruebas analíticas,
* exploración inicial,
* prototipos,
* EDA.

**Importante:**
La lógica productiva de la app no debería quedarse únicamente en notebooks. Cuando algo ya sirve para la aplicación, debería pasar a `app/services/` u otra capa más estable.

---

## Carpeta `tests/`

Aquí deben ir las pruebas automáticas del proyecto.

Una prueba automática es código que verifica si otra parte del sistema funciona correctamente.

Ejemplos de pruebas futuras:

* validar que el cargador de datos funciona,
* verificar transformaciones,
* comprobar que ciertos resultados esperados se mantengan.

Aunque ahora esté vacía, es correcto tenerla desde el inicio porque deja preparado el proyecto para crecer con buenas prácticas.

---

## Recomendaciones de uso del proyecto

### 1. Mantener responsabilidades separadas

* `pages/` para interfaz.
* `services/` para lógica.
* `config/` para configuración.
* `components/` para piezas reutilizables.

---

### 2. Evitar lógica compleja en `main.py`

`main.py` debe coordinar la app, no contener toda la implementación.

---

### 3. No subir archivos temporales

Evitar versionar:

* `__pycache__/`
* `*.pyc`
* entornos virtuales
* archivos de sistema

---

### 4. Mover a servicios todo lo que crezca

Si una página empieza a tener mucho código de procesamiento, ese código debería moverse a `services/`.

---

### 5. Usar `notebooks/` solo para exploración

Lo que quede en producción debe migrarse a módulos del proyecto.

---

## Flujo general recomendado

1. Desarrollar páginas en `app/pages/`.
2. Crear componentes reutilizables en `app/components/`.
3. Implementar lógica en `app/services/`.
4. Centralizar parámetros en `app/config/settings.py`.
5. Probar localmente con Poetry.
6. Subir cambios al repositorio.
7. Desplegar la app desde `main`.

---

## Ejecución local

```bash
poetry run streamlit run app/main.py
```

---

## Despliegue

La aplicación está preparada para desplegarse en **Streamlit Community Cloud**, usando:

* rama `main`,
* archivo principal `app/main.py`.

---

## Estado actual

Actualmente esta estructura corresponde a una base inicial, lista para:

* seguir desarrollando páginas,
* integrar analítica,
* agregar servicios,
* incorporar pruebas,
* escalar el proyecto de forma ordenada.
