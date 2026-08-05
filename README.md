# WE App - Personal Planner & Tracker

A lightweight, fast, and responsive web application built with Python and FastAPI to help you track and manage your daily activities, specifically focusing on food spots, study spots, and personal planning.

## 🚀 Features

* **Food Board:** A drag-and-drop kanban across three columns (Đã ăn / Chưa ăn / Muốn ăn), with photo thumbnails, a 0–5 star rating, and a one-tap Google Maps link per place.
* **Study Management:** Keep track of your study spots and edit them in place.
* **Daily Planning:** A todo list with priority badges, deadlines, and tick-to-complete.
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
│   ├── routes/          # API and View routers
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
│       ├── index.html
│       ├── food.html
│       ├── edit_food.html
│       ├── plan.html
│       ├── study.html
│       └── edit_study.html
├── we.db                # SQLite Database file (local development only)
├── requirements.txt     # Python dependencies
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

Tables are created on startup by `Base.metadata.create_all`, and `app/migrations.py`
adds any columns missing from an older database (`create_all` only creates whole
tables, never new columns on existing ones). Both run on every boot and are safe
to repeat.

Background videos are loaded per page by `base.html` from `app/static/`:
`bghome.mp4` (home + study) and `bgfood.mp4` (food + plan).

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

> The background videos (~1.4 MB each) are part of the deployment. If you swap in
> heavier files, host them on a CDN or Vercel Blob and point the `<source src>`
> in `base.html` at that URL instead.

### Other platforms

The included `Procfile` also makes this deployable on Heroku, Render, or Railway.

## 📄 License

This project includes a `LICENSE` file. Please refer to it for specific usage and distribution rights.
