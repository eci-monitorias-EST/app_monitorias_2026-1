FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --without dev

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
