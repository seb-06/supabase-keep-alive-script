#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -gt 0 && "$1" == "add-db" ]]; then
    shift
    exec /app/add_database "$@"
fi

exec "$@"
