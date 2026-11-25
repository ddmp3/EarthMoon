# Build context = repository ROOT:
#   docker build -f apps/discovery/Dockerfile -t earthmoon-discovery .
# Internal service (ADR-005): no public port; the Node API calls it on the Compose network.
FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RELEASES_DIR=/data/releases
WORKDIR /srv
COPY tools/discovery/requirements.txt tools-requirements.txt
COPY apps/discovery/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r tools-requirements.txt -r requirements.txt
COPY data/ui /srv/data/ui
COPY data/catalog /srv/data/catalog
COPY data/geology /srv/data/geology
COPY data/presets /srv/data/presets
COPY data/validation /srv/data/validation
COPY tools/discovery /srv/tools/discovery
COPY apps/discovery /srv/apps/discovery
WORKDIR /srv/apps/discovery
USER nobody
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
