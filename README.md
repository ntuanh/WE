# WE App - Personal Planner & Tracker

A lightweight, fast, and responsive web application built with Python and FastAPI to help you track and manage your daily activities, specifically focusing on food spots, study spots, and personal planning.

## 🚀 Features

* **Food Board:** A drag-and-drop kanban across three columns (Đã ăn / Chưa ăn / Muốn ăn), with photo thumbnails, a 0–5 star rating, and a one-tap Google Maps link per place.
* **Study Management:** Keep track of your study spots and edit them in place.
* **Daily Planning:** A todo list with priority badges, deadlines, and tick-to-complete.
* **Shared Timetable:** A weekly hour-by-hour timetable per account, plus ♥ special days that put both people's timelines side by side and draw the connection between them — the windows where you are *both* free, and the hours you are both booked.
* **Login Gate:** Every page sits behind a username/password form — two accounts, one of them admin. Passwords are PBKDF2 hashes, the session is an HMAC-signed cookie, and repeated wrong guesses lock the account out for a while.
* **Glass Aesthetic:** Frosted-glass panels over a full-bleed video background, with a warm oklch palette and responsive breakpoints down to mobile.
* **Interactive UI:** Background videos for an immersive experience, and an auto-highlighting nav bar.

## 🛠️ Tech Stack

This project leverages the following technologies:

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) for high-performance API routing and server logic.
* **Server:** Uvicorn as the ASGI web server.
* **Database:** **SQLAlchemy** ORM over SQLite (`we.db`) locally, or Postgres in production via `DATABASE_URL`. Database operations live in `crud.py`.
* **Frontend:** HTML5, CSS3, JavaScript, and **Jinja2** for templating.
* **Form Handling:** `python-multipart` for processing HTML form data.
* **Hosting:** Vercel serverless (`api/index.py` + `vercel.json`).

## 📁 Project Structure

```text
.
├── api/
│   └── index.py         # Vercel entrypoint — re-exports the ASGI app
├── app/
│   ├── __init__.py
│   ├── main.py          # Application entry point and FastAPI instance
│   ├── database.py      # Engine: Postgres via DATABASE_URL, else SQLite
│   ├── migrations.py    # Adds new columns to a pre-existing database
│   ├── templating.py    # Jinja2 with absolute paths (needed on serverless)
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic models for data validation
│   ├── crud.py          # Create, Read, Update, Delete database functions
│   ├── auth.py          # Accounts, password hashing, signed session cookie
│   ├── log.py           # Startup logging that can't crash on a cp1252 console
│   ├── users.example.json  # Template for the account file (committed)
│   ├── users.local.json    # Real password hashes — git-ignored, never pushed
│   ├── routes/          # API and View routers
│   │   ├── auth.py      # Login / logout routes
│   │   ├── schedule.py  # Shared-calendar routes
│   │   ├── food.py      # Food-related routes
│   │   ├── plan.py      # Planning-related routes
│   │   └── study.py     # Study-related routes
│   ├── static/          # Static assets (CSS, JS, background MP4s)
│   │   ├── style.css
│   │   ├── script.js
│   │   ├── bgfood.mp4
│   │   └── bghome.mp4
│   └── templates/       # Jinja2 HTML templates
│       ├── base.html
│       ├── schedule.html
│       ├── index.html
│       ├── food.html
│       ├── edit_food.html
│       ├── plan.html
│       ├── edit_plan.html
│       ├── study.html
│       └── edit_study.html
├── tests/               # pytest suite — see Tests below
│   ├── conftest.py      # in-memory DB + throwaway accounts
│   ├── test_auth.py
│   ├── test_crud.py
│   ├── test_database.py
│   └── test_routes.py
├── we.db                # SQLite Database file — local only, git-ignored
├── requirements.txt     # Python dependencies
├── requirements-dev.txt # Adds pytest + httpx for the test suite
├── vercel.json          # Vercel build + routing configuration
├── Procfile             # Deployment configuration for Heroku/Render/Railway
└── README.md            # Project documentation
```

## ⚙️ Installation & Local Setup

**1. Clone the repository**

```bash
git clone https://github.com/ntuanh/WE.git
cd WE
```

**2. Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

**3. Install dependencies**

Install the required packages listed in the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

**4. Run the application**

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

*The application will be available at <http://127.0.0.1:8000>.*

`we.db` is created automatically on first run, so no migration step is needed.

## 🗄️ Database

On every boot the app does two things, both safe to repeat:

1. `Base.metadata.create_all` creates any **table** that does not exist yet.
2. `app/migrations.py` adds any **column** that `models.py` declares but the
   live database is missing — `create_all` never alters an existing table.

Step 2 is derived from the models themselves, so **adding a field to
`models.py` is the whole job**: restart, and the column appears on the existing
database with your rows untouched. There is no hand-written column list to keep
in sync, and no reason to ever delete `we.db` to pick up a schema change.

Startup prints which database it picked and any columns it patched:

```
[startup] database: sqlite -> D:\SoloWorks\WE\we.db
[startup] da va schema: plans.priority, plans.deadline
```

`GET /healthz` reports the same thing at runtime.

### Where the data lives

Resolved in this order by `app/database.py`:

| Setting | Used for | Survives a redeploy? |
| --- | --- | --- |
| `DATABASE_URL` | Postgres — **use this in production** | yes |
| `SQLITE_PATH` | SQLite on a mounted volume (Railway, Fly) | yes |
| *(nothing)* | `we.db` next to the code — local development | yes |
| *(nothing, read-only FS)* | `/tmp/we.db` on serverless | **no** — wiped on every cold start |

> ⚠️ **`we.db` must never be committed.** It used to be tracked in git, which
> meant every `git pull`, `git checkout`, or `git stash` overwrote your live
> data with whatever snapshot was in the last commit — the data "resetting on
> its own". It is in `.gitignore` now; keep it that way.

Background videos are loaded per page by `base.html` from `app/static/`:
`bghome.mp4` (home + study) and `bgfood.mp4` (food + plan).

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```

218 tests, no network and no touching `we.db` — `tests/conftest.py` points the
app at an in-memory SQLite before importing it, and swaps in throwaway accounts
so the real password hashes are never needed.

| File | Covers |
| --- | --- |
| `tests/test_auth.py` | password hashing, login, brute-force lockout, session cookie forgery/expiry, the login gate on every page |
| `tests/test_database.py` | the "new column, old database" case, repeat-safe migrations, data surviving a restart, database selection |
| `tests/test_crud.py` | input cleaning and validation, time parsing, week maths, calendar ownership rules |
| `tests/test_routes.py` | each page and form end-to-end over HTTP |

## 🗓 Shared timetable

`/schedule` gives each account its own week timetable — hours down the side,
Mon–Sun across, entries drawn as blocks against the clock. The accounts come from
`auth.USERS`, so nobody's name is hard-coded and the page follows whatever two
logins exist.

The hour window is not fixed at 00:00–24:00, which would leave most of the grid
empty. It defaults to 07:00–22:00 and stretches only as far as the week's earliest
and latest entry actually reach.

Entries that overlap are split into lanes and drawn side by side. Without that the
later one renders on top of the earlier and hides it completely, which looks exactly
like the entry was never saved.

Clicking a day header — or any block in it — expands that day's panel below the
grid to read, add, edit or delete. The panel is rendered server-side and hidden,
the script only flips `hidden`, and a submit redirects back with
`?open=<account>:<date>` so the day you were working on is still open when the
page comes back. Clicking a block also opens that entry's edit form directly.

### ♥ Special days and the connection between them

Any day can be marked ♥ with a reason ("Kỷ niệm 2 năm"). A special day is shared,
not per-person — `special_days` has no `owner` column, so marking it from either
timetable marks it for both.

Special days get pinned above the week as **two timelines on one hour axis**, one
person per side, with the connection drawn down the middle:

* **♥ rảnh cùng nhau** — a solid band wherever *both* calendars are empty, so the
  windows you could actually spend together are the most visible thing on the page.
  Gaps shorter than `FREE_MINUTES` (45) are dropped: a ten-minute crack between two
  classes is not a window.
* **✕ cả hai đều bận** — a hatched band where both are booked.

Both are computed as interval intersections: merge each person's entries into busy
spans, take the complement for free spans, then intersect the two sides. A summary
line adds up each ("Rảnh cùng nhau 9 tiếng"), and the free windows repeat as chips
under the timelines.

Entries store an optional `HH:MM` start and end. Leaving the start empty makes it
an all-day entry, shown as a chip in the day header rather than a block on the
axis. An end at or before the start is a typo, so it is pushed to start + 1 hour —
left alone it would render a block with negative height and break the grid. An
entry can only be filed under an account that exists: a bad `owner` is rejected
outright rather than quietly landing on the other person's timetable.

## 🔐 Accounts & passwords

**No accounts are hard-coded.** This repo is public and the salt is in
`app/auth.py`, so a hash committed here could be attacked offline by anyone.
Accounts are loaded at startup from, in order:

1. the `WE_USERS` environment variable — used in production
2. `app/users.local.json` — your machine, git-ignored

Both take the same JSON shape (see `app/users.example.json`):

```json
{
  "ntuanh":  { "hash": "<64 hex chars>", "role": "admin" },
  "trucngu": { "hash": "<64 hex chars>", "role": "user"  }
}
```

Generate a hash — PBKDF2-SHA256, 200k iterations, the password itself is never
stored:

```bash
python -m app.auth "the-new-password"
```

**Local setup:** copy `app/users.example.json` to `app/users.local.json` and
paste your hashes in. **Production:** paste the same JSON into the `WE_USERS`
env var. With neither configured, the login page says so instead of silently
rejecting every attempt.

After too many wrong guesses (`MAX_ATTEMPTS`, default 8) that username/IP pair
is refused for 5 minutes, correct password included. The counter lives in
process memory, so on serverless each instance counts separately.

## ☁️ Deployment

### Vercel

The project ships with `vercel.json` and `api/index.py`, so importing the repo at
[vercel.com/new](https://vercel.com/new) is enough — every push to `main` then
deploys automatically.

**SQLite does not work on Vercel.** The filesystem is ephemeral, so a `.db` file
resets on every cold start. Create a free Postgres ([Neon](https://neon.tech),
[Supabase](https://supabase.com), or Vercel Postgres) and set it under
Project → Settings → Environment Variables:

```
DATABASE_URL = postgresql://user:pass@host/dbname
```

A `postgres://...` string works too — it is normalized automatically. Without
this variable the site still runs, backed by SQLite in `/tmp`, but anything you
save disappears on the next cold start — useful only for previewing the design.

Then two more, both required for the site to be usable and safe:

```
SECRET_KEY = <any long random string>
WE_USERS   = {"ntuanh": {"hash": "<64 hex chars>", "role": "admin"}}
```

`SECRET_KEY` signs the login cookie. Without it the app falls back to a
placeholder that is public in this repo, meaning anyone could forge a session.
Changing it invalidates every existing session, which is how you sign every
device out at once.

`WE_USERS` carries the accounts — see [Accounts & passwords](#-accounts--passwords).
Nothing logs in without it, since no accounts ship in the code.

`GET /healthz` reports whether each of these landed:

```json
{"ok": true, "database": "postgres -> …", "ephemeral": false,
 "bad_database_url": false, "secret_key_set": true}
```

> The background videos (~1.4 MB each) are part of the deployment. If you swap in
> heavier files, host them on a CDN or Vercel Blob and point the `<source src>`
> in `base.html` at that URL instead.

### Other platforms

The included `Procfile` also makes this deployable on Heroku, Render, or Railway.

## 📄 License

This project includes a `LICENSE` file. Please refer to it for specific usage and distribution rights.
