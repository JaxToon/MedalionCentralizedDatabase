FROM python:3.11-slim

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

RUN useradd --create-home --uid 1000 appuser
USER appuser

# One image, two services: docker-compose.yml sets the command for api and frontend.
