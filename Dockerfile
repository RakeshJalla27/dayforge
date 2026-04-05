# syntax=docker/dockerfile:1
# Works on both ARM64 (Raspberry Pi 4/5) and AMD64 (AWS EC2)
FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies before copying source for better layer caching.
# uv creates .venv inside /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy application source
COPY . .

EXPOSE 8765

# Run directly from the venv uv created — no uv overhead at runtime
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "server.py"]
