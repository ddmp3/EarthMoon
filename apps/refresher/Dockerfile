# Build context = repository ROOT. The refresher (T52, ADR-009 section 5): the only container with outbound network
# (restricted in code to the catalogue hosts, tools/discovery/watch.py) and the only one that writes the data folder.
# No port. Started only on request: docker compose --profile refresh up -d refresher
FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv/tools
WORKDIR /srv
COPY tools/discovery/requirements.txt tools-requirements.txt
RUN pip install --no-cache-dir -r tools-requirements.txt
COPY data/catalog /srv/data/catalog
COPY tools/discovery /srv/tools/discovery
USER nobody
CMD ["python", "-m", "discovery.refresher", "loop", "--state", "/data/refresh/state.json", "--releases", "/data/releases"]
