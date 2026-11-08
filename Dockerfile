# DFDI web app: viewer + drawing page + measurement engine
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    DFDI_DATA=/data

WORKDIR /app
COPY requirements.lock .
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir -r requirements.lock

COPY src ./src
COPY app ./app
COPY tests ./tests
COPY pyproject.toml README.md ./

# non-root user; patient data lives only in the /data volume
RUN useradd --create-home --uid 1000 dfdi && mkdir -p /data && chown dfdi:dfdi /data
USER dfdi

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/cases', timeout=4)" || exit 1

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
