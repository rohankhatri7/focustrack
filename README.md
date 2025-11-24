# FocusTrack (Flask web app)

FocusTrack is a small Flask web app that helps college students track tasks. It uses SQLite with SQLAlchemy models and simple managers to keep database logic clean.

## Folder layout
- `main.py` - Flask routes and entry point.
- `database.py` - SQLite engine and session helpers.
- `models.py` - ORM models for tasks, categories, reminders.
- `managers.py` - Manager classes that wrap CRUD operations.
- `templates/` - HTML templates for dashboard, tasks, calendar.
- `static/` - CSS file for light styling.
- `README.md` - this file.
- `ARCHITECTURE_NOTES.md` - presentation-friendly summary.

## Setup
```bash
cd focustrack
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install flask sqlalchemy
```

## Run the app
```bash
cd focustrack
python main.py
```
Open http://127.0.0.1:5000 in your browser.

## OOP concepts
- **Inheritance**: `BaseModel` -> `Task`, `Category`, `Reminder`; `BaseManager` -> `TaskManager`, `CategoryManager`, `ReminderManager`.
- **Encapsulation**: managers hide all database session work; routes call manager methods instead of raw queries.
- **Polymorphism**: models override `summary()`; managers can override `get_model_class()` to describe the model they handle.

## Architecture
- `database.py` sets up the engine, Base, and session factory.
- `models.py` defines ORM models and shared helpers.
- `managers.py` contains CRUD logic and validation so the Flask routes stay simple.
- `main.py` creates the Flask app, global managers, and routes for dashboard, tasks, and calendar pages.
- `templates/` holds the HTML; `static/style.css` adds light styling.

## Future work: GCP deployment
This app can be containerized (for example with a small Python base image) and deployed to Google Cloud Run. A Docker image would serve the Flask app, while Cloud SQL or a managed database could replace the local SQLite file. This keeps local development simple and allows an easy path to a managed deployment later.
