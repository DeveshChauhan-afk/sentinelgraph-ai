#!/bin/sh
set -e

# =======================================================================
# SentinelGraph AI - API Container Entrypoint
# =======================================================================

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Database migrations applied successfully."
fi

# Honor dynamic PORT environment variable (e.g. Render Web Services)
if [ "$1" = "uvicorn" ] && [ "$2" = "app.main:app" ]; then
    PORT="${PORT:-8000}"
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi

exec "$@"
