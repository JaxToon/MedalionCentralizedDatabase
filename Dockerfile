FROM python:3.11.18-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

COPY alembic.ini .
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY frontend ./frontend

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/storage \
    && chown appuser:appuser /app/storage
USER appuser

# One image, two services. The default command migrates the database and serves the
# API; docker-compose.yml overrides it for the frontend (Streamlit on 8501).
EXPOSE 8000 8501
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
