FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY policies ./policies
COPY prompts ./prompts
COPY migrations ./migrations
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN pip install --upgrade pip && pip install ".[dev]"     && chmod +x /app/docker-entrypoint.sh     && useradd --create-home --uid 10001 steh     && mkdir -p /tmp/steh-workspaces     && chown -R steh:steh /app /tmp/steh-workspaces

USER steh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
