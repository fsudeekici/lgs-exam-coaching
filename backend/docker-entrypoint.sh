#!/bin/sh
set -e

# Bring the database up to date, then make sure subjects, topics and the first admin exist.
alembic upgrade head
python -m app.seed

# nginx is the only client, so its forwarded headers are trusted.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"
