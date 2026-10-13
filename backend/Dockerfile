FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY seed ./seed
COPY app ./app
COPY --chmod=755 docker-entrypoint.sh ./

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
