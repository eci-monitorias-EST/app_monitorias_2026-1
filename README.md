[project]
name = "monitorias"
version = "0.1.0"
description = ""
authors = [
    {name = "RamiroSeb",email = "juanrayala12@gmail.com"}
]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "streamlit (>=1.55.0,<2.0.0)",
    "pandas (>=2.2,<3.0)",
    "plotly (>=6.6.0,<7.0.0)",
    "dvc (>=3.67.0,<4.0.0)",
    "requests (>=2.32.0,<3.0.0)"
]
[tool.poetry]
package-mode = false

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[dependency-groups]
dev = [
    "pytest (>=9.0.2,<10.0.0)",
    "black (>=26.3.1,<27.0.0)"
]