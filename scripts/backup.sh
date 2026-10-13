#!/usr/bin/env bash
# Dump the production database to a dated, compressed file and delete old dumps.
#
# Run it daily from cron on the server, for example at 03:00:
#   0 3 * * * /path/to/lgs-exam-coaching/scripts/backup.sh >> /var/log/lgs-backup.log 2>&1
#
# Settings (from .env or the environment): BACKUP_DIR (default ./backups),
# BACKUP_KEEP_DAYS (default 14).
set -euo pipefail

cd "$(dirname "$0")/.."

# Use BACKUP_* from .env unless they are already set in the environment.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    case "$key" in
      BACKUP_DIR | BACKUP_KEEP_DAYS) [ -n "${!key:-}" ] || export "$key=$value" ;;
    esac
  done < .env
fi

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
COMPOSE=(docker compose -f docker-compose.prod.yml)

# Dumps hold personal data: readable by the owner only.
umask 077
mkdir -p "$BACKUP_DIR"

file="$BACKUP_DIR/lgs_$(date +%Y%m%d_%H%M%S).sql.gz"
tmp="$file.partial"
trap 'rm -f "$tmp"' EXIT

"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' | gzip > "$tmp"

# A dump always ends with this line; without it the dump is incomplete.
if ! gunzip -c "$tmp" | tail -n 5 | grep -q "PostgreSQL database dump complete"; then
  echo "$(date "+%F %T") backup FAILED: dump is incomplete" >&2
  exit 1
fi

mv "$tmp" "$file"
find "$BACKUP_DIR" -name "lgs_*.sql.gz" -type f -mtime "+$BACKUP_KEEP_DAYS" -delete

echo "$(date "+%F %T") backup written: $file ($(du -h "$file" | cut -f1))"
