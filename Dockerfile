# ==============================================================================
# Dockerfile Reproducible para el Sistema de Agente Financiero (ITBA C3/C14)
# ==============================================================================
FROM python:3.12-slim

# Instalar dependencias del sistema y gestor uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv directamente
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copiar dependencias y archivo de bloqueo
COPY pyproject.toml uv.lock ./

# Instalar dependencias fijadas de producción
RUN uv sync --frozen --no-dev

# Copiar el código fuente y assets
COPY src/ ./src/
COPY Docs/ ./Docs/
COPY data/ ./data/

# Exponer el puerto estándar de Streamlit
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando de ejecución de la interfaz
ENTRYPOINT ["uv", "run", "streamlit", "run", "src/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
