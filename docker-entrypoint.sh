#!/bin/sh
set -e

# Docker Compose runs migrations once in the `migrate` service and starts
# `api` and `worker` with RUN_MIGRATIONS=false (ADR-016).
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi

if [ "$#" -eq 0 ]; then
    set -- uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

exec "$@"
