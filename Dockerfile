FROM python:3.11-slim

# libgomp1 is needed by onnxruntime/torch for OpenMP threading on slim images
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Lightweight by default (fits ~512MB-RAM hosts; chatbot falls back to direct
# passage retrieval automatically — see backend/services/llm.py). Swap to
# requirements-full.txt below for the precise QA-model answers on a host
# with more RAM headroom (e.g. Cloud Run with --memory 2Gi).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1

# Cloud Run injects $PORT; default to 8080 for local `docker run` testing.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
