FROM python:3.11-slim AS base

WORKDIR /app

# Persist downloaded model weights in the mounted ./models volume instead of
# re-downloading ~1GB from HuggingFace on every container restart.
ENV HF_HOME=/app/models

# System deps for torch CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir . 

COPY src/ src/
COPY models/ models/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
