# Backend image for AI Pharmacy OS.
# Build context: ./backend
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for asyncpg/bcrypt builds are covered by wheels; keep image lean.
COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

EXPOSE 8000
CMD ["uvicorn", "pharmacy_os.main:app", "--host", "0.0.0.0", "--port", "8000"]
