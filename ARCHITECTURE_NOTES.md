# FocusTrack architecture notes

- `main.py` creates the Flask app, sets up auth routes (signup/login/logout), and global managers: `TaskManager`, `CategoryManager`, and `ReminderManager`. These share one SQLAlchemy session from `database.py`.
- Routes call manager methods to create, list, update, or delete tasks. The routes stay short because the managers handle validation and commits. Tasks are filtered per logged-in user.
- `models.py` defines `Task`, `Category`, `Reminder`, and `User` directly from the SQLAlchemy Base. IDs and relationships are declared inline to keep it simple.
- `BaseManager` holds shared session logic; `TaskManager` and `CategoryManager` inherit from it to avoid duplicating commit and query helpers.
- `database.py` is responsible only for the engine, Base, and session factory. No Flask code lives there, which keeps responsibilities clear.
- Templates in `templates/` render data returned by the routes. The tasks page uses a Kanban layout; the calendar shows descriptions on hover. Templates do not talk to the database directly.
- Running `python main.py` starts the Flask development server so the dashboard, tasks page, and calendar page are available in the browser.
