FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    APP_CONFIG_YAML=app/config/app.yaml \
    PERSISTENCE_STORE=sqlite \
    SQLITE_PATH=/app/data/processed/app.db \
    STREAMLIT_SERVER_PORT=8501

WORKDIR /app

COPY pyproject.toml README.md ./
RUN uv sync --no-dev --no-install-project

COPY app ./app
COPY data ./data
RUN mkdir -p /app/data/processed \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

CMD ["sh", "-c", "streamlit run app/main.py --server.port=${STREAMLIT_SERVER_PORT:-8501} --server.address=0.0.0.0"]
