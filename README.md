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
python -m app.seed --demo     # subjects, topics + admin; --demo adds sample people and data
uvicorn app.main:app --reload
```

Frontend (http://localhost:5173, proxies `/api` to the backend):

```sh
cd frontend
npm install
npm run dev
```

`--demo` adds three students, a parent linked to the first one, four exams with results,
30 days of question logs, topic progress and two coach notes. It never overwrites existing data.

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

## Student analytics

Clicking a student's name opens their detail page: the last exam against the one before it,
net trend over exams (total and per subject), weak topics, and the student's
average per subject next to the average of all students who took the same exams.

A topic is weak when it was marked wrong in at least 2 of the student's last 3 exams. The same
rule is used everywhere weak topics appear (admin, student and parent views).

## Student panel

Students log in to a phone-friendly panel with three tabs:

- **Soru takibi**: daily question log (date, subject, topic, solved, correct, wrong). The topic
  is optional, and "solved" left empty counts as correct + wrong.
- **Konular**: mark each topic as not started, studying, done or needs review.
- **Denemeler**: their own exam analytics, the same view the admin has, read only.

The admin sees a student's question logs (last 30 days) and topic progress at the bottom of
the student detail page.

## Parent panel and coach notes

Parents log in to a short summary for each child linked to them: last exam, total net trend,
weak topics, and questions solved in the last 7 days.

On the student detail page the admin writes coach notes and chooses per note whether the
parent can see it. Parents see only the visible ones.

## Multiple admins

The admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD` is the main admin. Under "Yöneticiler" they add
more admins (coaches), edit them and deactivate them. Each coach only sees the students they
added themselves and those students' parents; exams are shared, but a coach only sees and enters
results for their own students. The main admin sees every student and parent. When upgrading,
existing students and parents are given to the existing admin.

## Admin overview and parent meetings

The admin's home page ("Genel bakış") lists every active student with their last exam net, the
change from the exam before it, questions solved in the last 7 days, and the number of weak
topics. A student with no question log in the
last 3 days is flagged.

"Veli görüşmesi sayfası" on the student detail page opens one page to show at a parent
meeting: summary cards, net trend, subject comparison, weak topics, questions in the last 30
days, topic progress, and the coach notes marked visible to parents. "Yazdır / PDF kaydet"
prints it or saves it as a PDF through the browser's print dialog. After each meeting the admin
adds a dated meeting note at the bottom of that page; these notes are only visible to the admin.

## Subjects and topics

`backend/seed/lgs_topics_seed.json` is the only source for subjects (including `short_name` and `session`) and topics. After editing it,
run `python -m app.seed`. Topics removed from the file are deleted from the database, except
those already used in recorded exam mistakes, which are kept and reported.

## Scoring

Net = correct − wrong / 3. `exam_results.net` is a generated column in PostgreSQL;
`app.services.scoring.calculate_net` is the same rule in Python.

## Accounts and privacy

- Every user is shown the KVKK privacy notice (aydınlatma metni) on first login and must accept
  it before using the app; the date is stored. The notice is also public at `/kvkk`.
- A student cannot log in until the admin ticks "Veli onayı alındı" on the student form and
  enters the date the parent's consent was received. Unticking it later signs the student out.
- A login lasts 8 hours (`ACCESS_TOKEN_EXPIRE_MINUTES`), or 30 days (`REMEMBER_ME_DAYS`) when
  "Beni hatırla" is ticked on the login form. "Çıkış yap" removes the session from that device.
- Passwords need at least 6 characters; there are no other rules.
- Users change their own password under "Hesabım" (click your name in the header). The admin
  resets a student's or parent's password from the edit form on the Öğrenciler / Veliler pages.
  Any password change signs that user out everywhere else, remembered sessions included.
- After 5 wrong passwords for one email within 15 minutes, logins for that email are blocked
  until the window passes (`LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_MINUTES`). The admin sees a
  "Giriş engelli" badge on that user and can lift the block from their edit form.
- The site asks search engines not to index it (`robots.txt`, a `noindex` meta tag, and an
  `X-Robots-Tag` header in production).

## Production deployment

The production stack is three containers: PostgreSQL, the backend, and nginx serving the built
frontend and passing `/api` to the backend. Only nginx publishes a port.

### Before the first deploy

1. Fill in the data controller details in `frontend/src/kvkk.ts` (name, address, email, server
   location). **The notice text in `frontend/src/components/KvkkNotice.tsx` is a template, not
   legal advice. Have it reviewed by a lawyer**, in particular how consent is collected for
   students under 18.
2. On the server, install Docker with the Compose plugin and clone this repository.
3. Create the settings file and fill in every value:

   ```sh
   cp .env.example .env
   chmod 600 .env
   ```

   `JWT_SECRET` must be at least 32 random characters (`openssl rand -hex 32`); the backend
   refuses to start with a short or placeholder secret or admin password.

### Deploy

```sh
docker compose -f docker-compose.prod.yml up -d --build
```

On every start the backend applies database migrations, updates subjects and topics from
`backend/seed/lgs_topics_seed.json`, and creates the admin from `ADMIN_EMAIL` /
`ADMIN_PASSWORD` if no user has that email yet. Then:

1. Open the site, log in as the admin, accept the notice, and change the password under
   "Hesabım".
2. Add students and parents, and record each student's parent consent so they can log in.
   Do not run the `--demo` seed in production.

To update later: `git pull`, then run the same `up -d --build` command.

Useful commands:

```sh
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

### HTTPS

nginx in this stack serves plain HTTP on `HTTP_PORT`. **Do not expose it to the internet
without HTTPS**: passwords and student data would travel unencrypted. Put a TLS-terminating
proxy in front, for example Caddy on the same server with `HTTP_PORT=8080` in `.env`:

```
ornek-alan-adi.com {
    reverse_proxy localhost:8080
}
```

In that case also make sure port 8080 is closed to the outside in the firewall.

### Backups

`scripts/backup.sh` writes a compressed dump of the database to `BACKUP_DIR` (default
`./backups`) and deletes dumps older than `BACKUP_KEEP_DAYS` (default 14). Run it daily from
cron on the server:

```
0 3 * * * /path/to/lgs-exam-coaching/scripts/backup.sh >> /var/log/lgs-backup.log 2>&1
```

It exits with an error, and keeps no partial file, if the dump fails. The dumps contain
personal data and sit on the same server as the database: copy them somewhere else as well,
and try a restore once before you rely on them.

Restore a dump (this replaces the current data):

```sh
gunzip -c backups/lgs_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Tests

```sh
cd backend && pytest
```

The API tests need PostgreSQL running. They use a separate database, named after the one in
`DATABASE_URL` with `_test` appended (created automatically), or `TEST_DATABASE_URL` if set.
