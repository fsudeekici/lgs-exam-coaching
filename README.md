# LGS Exam Coaching

Web app for coaching students through LGS mock exams. Roles: admin, student, parent.

- `backend/` — FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT auth
- `frontend/` — React (Vite), Tailwind

## Run locally

Database:

```sh
docker compose up -d
```

Backend (http://localhost:8000, API docs at `/docs`):

```sh
cd backend
pip install -r requirements.txt
cp .env.example .env          # then set JWT_SECRET and ADMIN_PASSWORD
alembic upgrade head
python -m app.seed --demo     # subjects, topics + admin; --demo adds students and a parent
uvicorn app.main:app --reload
```

Frontend (http://localhost:5173, proxies `/api` to the backend):

```sh
cd frontend
npm install
npm run dev
```

Demo logins created by `--demo` (local development only): `student@example.com`,
`student2@example.com`, `student3@example.com` and `parent@example.com`, password `demo1234`. The admin login comes from `ADMIN_EMAIL` /
`ADMIN_PASSWORD` in `.env`.

## Entering exam results

The admin creates an exam (name, date, publisher), then enters each student's results on the
exam page: correct, wrong and blank for all six subjects in one form, plus optional wrong
topics per subject. Correct + wrong + blank must equal the subject's question count; a blank
count left empty is filled in automatically.

## Scoring

Net = correct − wrong / 3. `exam_results.net` is a generated column in PostgreSQL;
`app.services.scoring.calculate_net` is the same rule in Python.

## Tests

```sh
cd backend && pytest
```
