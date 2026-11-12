# TokenMaliyet — üretim imajı
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Bağımlılıklar önce (katman önbelleği)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY migrations ./migrations
COPY alembic.ini .
COPY scripts ./scripts

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data/raw \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
