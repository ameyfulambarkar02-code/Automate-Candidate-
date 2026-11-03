#!/bin/sh
set -e
if [ "$APP_ROLE" = "web" ]; then
  alembic upgrade head
fi
exec "$@"
