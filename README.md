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

## Students and parents

Under "Öğrenciler" the admin adds and edits students (name, email, password, school, class) and
deactivates them. A deactivated student cannot log in and is no longer offered for result entry,
but keeps their exam results. Under "Veliler" the admin adds parents and links them to students.

## Subjects and topics

`backend/seed/lgs_topics_seed.json` is the only source for subjects and topics. After editing it,
run `python -m app.seed`. Topics removed from the file are deleted from the database, except
those already used in recorded exam mistakes, which are kept and reported.

## Scoring

Net = correct − wrong / 3. `exam_results.net` is a generated column in PostgreSQL;
`app.services.scoring.calculate_net` is the same rule in Python.

## Tests

```sh
cd backend && pytest
```

The API tests need PostgreSQL running. They use a separate database, named after the one in
`DATABASE_URL` with `_test` appended (created automatically), or `TEST_DATABASE_URL` if set.
