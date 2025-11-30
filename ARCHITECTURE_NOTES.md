# FocusTrack architecture notes

- `main.py` creates the Flask app and sets up global managers: `TaskManager`, `CategoryManager`, and `ReminderManager`. These share one SQLAlchemy session from `database.py` to talk to the SQLite file.
- Routes call manager methods to create, list, update, or delete tasks. The routes stay short because the managers handle validation and commits. This is the main example of encapsulation.
- `models.py` defines `Task`, `Category`, `Reminder`, and `User` directly from the SQLAlchemy Base. IDs and relationships are declared inline to keep it simple.
- `BaseManager` holds shared session logic; `TaskManager` and `CategoryManager` inherit from it to avoid duplicating commit and query helpers.
- `database.py` is responsible only for the engine, Base, and session factory. No Flask code lives there, which keeps responsibilities clear.
- Templates in `templates/` render data returned by the routes. They do not talk to the database directly; they just display data passed from manager results.
- Running `python main.py` starts the Flask development server so the dashboard, tasks page, and calendar page are available in the browser.
