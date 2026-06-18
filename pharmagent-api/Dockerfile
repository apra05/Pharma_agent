FROM python:3.11-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory.
WORKDIR /app

# Install the application dependencies.
# The lock file uses pytorch-cpu index for Linux (CPU-only torch ~250MB vs 730MB GPU).
COPY uv.lock pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

# Copy the application into the container.
COPY src/pharma_agent pharma_agent/
COPY tools tools/

CMD ["/app/.venv/bin/fastapi", "run", "pharma_agent/infrastructure/api.py", "--port", "8000", "--host", "0.0.0.0"]
