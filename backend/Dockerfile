FROM python:3.12-slim

# Install system build dependencies (required for building C++ extensions like annoy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy lockfile, pyproject.toml, and README.md
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen

# Copy the rest of the application
COPY backend ./backend

# Run the FastAPI application using the virtual environment
CMD ["/app/.venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
