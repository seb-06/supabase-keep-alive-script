#!/usr/bin/env bash
set -euo pipefail

DATABASE_FILE="${DATABASE_FILE:-/app/databases.txt}"
name=""

usage() {
    echo "Usage: $0 [-n database-name] <database-url> <database-key>"
    exit 1
}

while getopts ":n:" opt; do
    case "$opt" in
        n) name="$OPTARG" ;;
        *) usage ;;
    esac
done

shift $((OPTIND - 1))
[[ $# -eq 2 ]] || usage

url="$1"
key="$2"

touch "$DATABASE_FILE"

if [[ -z "$name" ]]; then
    max_num=$(
        awk -F'|' '
            $1 ~ /^database-[0-9]+$/ {
                sub(/^database-/, "", $1)
                if ($1 > max) max = $1
            }
            END { print max + 1 }
        ' "$DATABASE_FILE"
    )
    name="database-$max_num"
fi

if awk -F'|' -v wanted="$name" '$1 == wanted { found=1 } END { exit !found }' "$DATABASE_FILE"; then
    echo "Error: database '$name' already exists."
    exit 1
fi

printf '%s|%s|%s\n' "$name" "$url" "$key" >> "$DATABASE_FILE"
echo "Added database '${name}' to ${DATABASE_FILE}"
