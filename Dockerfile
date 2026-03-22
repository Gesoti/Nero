FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Layer-cache: install dependencies before copying source
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ app/
COPY main.py .

ENV WL_ENABLED_COUNTRIES=cy,gr,es,pt,cz,at,it,fi,no,ch,bg,de,pl \
    WL_HOST=0.0.0.0 \
    WL_PORT=8000

# Symlink /app/data → /data so relative paths (data/cy/water.db) land on the
# persistent volume mounted at /data on the host.
RUN ln -s /data /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD [".venv/bin/python", "main.py"]
