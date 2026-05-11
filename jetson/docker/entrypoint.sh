#!/bin/bash
# Runs as root at container startup.
# Fixes ownership on mounted volumes, then drops to the sentry user.
set -e
chown -R sentry:sentry /app/state /app/logs
exec gosu sentry "$@"
