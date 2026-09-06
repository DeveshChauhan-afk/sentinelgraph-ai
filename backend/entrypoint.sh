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

exec "$@"
