from datetime import date, datetime
import calendar

from flask import Flask, g, redirect, render_template, request, session as flask_session, url_for
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from database import Base, engine, get_session
import models
from managers import CategoryManager, ReminderManager, TaskManager

# flask app + secret key for sessions
app = Flask(__name__)
app.secret_key = "dev-secret-key" #placeholder for now

# one shared session
db_session = get_session()
task_manager = TaskManager(db_session)
category_manager = task_manager.category_manager
reminder_manager = ReminderManager(db_session)

# make sure tables exist before handling requests
Base.metadata.create_all(engine)

def get_current_user():
    # look up the user_id stored in the session cookie and return the ORM user
    user_id = flask_session.get("user_id")
    if not user_id:
        return None
    return db_session.get(models.User, user_id)

@app.before_request
def require_login():
    # everything but auth/static should bounce to login if no user
    # storing on g so templates can check g.current_user too
    g.current_user = get_current_user()
    public_endpoints = {"login", "signup", "static"}
    if request.endpoint in public_endpoints or request.endpoint is None:
        return None
    if not g.current_user:
        return redirect(url_for("login"))
    return None

@app.route("/signup", methods=["GET", "POST"])
def signup():
    message = ""  # display erros on page
    if g.current_user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        # pull form fields
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not email or not password:
            message = "Email and password required."
        elif password != confirm:
            message = "Passwords have to match."
        else:
            # check if email already exists to keep it unique
            stmt = select(models.User).where(models.User.email == email)
            existing = db_session.execute(stmt).scalar_one_or_none()
            if existing:
                message = "Email already signed up. Try logging in."
            else:
                # hash the password and save the new user
                new_user = models.User(email=email, password_hash=generate_password_hash(password))
                db_session.add(new_user)
                try:
                    db_session.commit()
                except Exception:
                    db_session.rollback()
                    message = "Could not create user."
                else:
                    # send them to login so they can start using the app
                    return redirect(url_for("login"))
    return render_template("signup.html", message=message, active_page=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""  # basic error string
    if g.current_user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        stmt = select(models.User).where(models.User.email == email)
        user = db_session.execute(stmt).scalar_one_or_none()
        if user and check_password_hash(user.password_hash, password):
            # stash user id in session cookie
            flask_session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        else:
            message = "Bad email or password."
    return render_template("login.html", message=message, active_page=None)

@app.route("/logout")
def logout():
    flask_session.clear()
    return redirect(url_for("login"))

@app.route("/")
@app.route("/dashboard")
def dashboard():
    # pull all tasks for this user and calculate some quick stats
    tasks = task_manager.list_tasks(user_id=g.current_user.id)
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "Done")
    in_progress_tasks = sum(1 for t in tasks if t.status == "In Progress")
    pending_tasks = sum(1 for t in tasks if t.status == "Pending")

    if total_tasks > 0:
        percent_complete = int((completed_tasks / total_tasks) * 100)
        percent_in_progress = int((in_progress_tasks / total_tasks) * 100)
        percent_pending = 100 - percent_complete - percent_in_progress
    else:
        percent_complete = 0
        percent_in_progress = 0
        percent_pending = 0

    def sort_key(task):
        return task.due_date or "9999-12-31"

    upcoming = sorted(tasks, key=sort_key)[:5]
    recent_tasks = sorted(tasks, key=lambda t: t.created_at or "", reverse=True)[:5]

    counts_by_priority = {
        "high": sum(1 for t in tasks if t.priority == "High"),
        "medium": sum(1 for t in tasks if t.priority == "Medium"),
        "low": sum(1 for t in tasks if t.priority == "Low"),
    }
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        pending_tasks=pending_tasks,
        percent_complete=percent_complete,
        percent_pending=percent_pending,
        percent_in_progress=percent_in_progress,
        counts_by_priority=counts_by_priority,
        upcoming=upcoming,
        recent_tasks=recent_tasks,
    )


@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        # grab form inputs and hand off to the manager
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        status = request.form.get("status")
        category_name = request.form.get("category_name")
        try:
            task_manager.create_task(
                title, description, due_date, priority, status, category_name, user_id=g.current_user.id
            )
        except Exception:
            pass
        return redirect(url_for("tasks"))

    tasks_list = task_manager.list_tasks(user_id=g.current_user.id)
    categories = category_manager.list_categories()
    return render_template(
        "tasks.html",
        active_page="tasks",
        tasks=tasks_list,
        categories=categories,
        priorities=TaskManager.VALID_PRIORITIES,
        statuses=TaskManager.VALID_STATUS,
    )

# edit task
@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    # only edit tasks that belong to this user
    task = task_manager.get_task(task_id, user_id=g.current_user.id)
    if not task:
        return redirect(url_for("tasks"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        status = request.form.get("status") or task.status
        category_name = request.form.get("category_name")
        try:
            task_manager.update_task(
                task_id, title, description, due_date, priority, status, category_name, user_id=g.current_user.id
            )
        except Exception:
            pass
        return redirect(url_for("tasks"))

    categories = category_manager.list_categories()
    return render_template(
        "edit_task.html",
        active_page="tasks",
        task=task,
        categories=categories,
        priorities=TaskManager.VALID_PRIORITIES,
        statuses=TaskManager.VALID_STATUS,
    )

@app.route("/tasks/<int:task_id>/done", methods=["POST"])
def mark_done(task_id):
    task_manager.update_task_status(task_id, "Done", user_id=g.current_user.id)
    return redirect(url_for("tasks"))

@app.route("/tasks/<int:task_id>/move", methods=["POST"])
def move_task(task_id):
    new_status = request.json.get("status") if request.is_json else request.form.get("status")
    if new_status not in TaskManager.VALID_STATUS:
        return {"error": "bad status"}, 400
    ok = task_manager.update_task_status(task_id, new_status, user_id=g.current_user.id)
    if not ok:
        return {"error": "not found"}, 404
    return {"ok": True}

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    task_manager.delete_task(task_id, user_id=g.current_user.id)
    return redirect(url_for("tasks"))

@app.route("/calendar", endpoint="calendar")
def calendar_view():
    # visual calendar
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    tasks_by_date = {}
    for task in task_manager.list_tasks(user_id=g.current_user.id):
        if task.due_date:
            try:
                d = datetime.strptime(task.due_date, "%Y-%m-%d").date()
                tasks_by_date.setdefault(d, []).append(task)
            except Exception:
                pass

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return render_template(
        "calendar.html",
        active_page="calendar",
        year=year,
        month=month,
        month_name=calendar.month_name[month],
        weeks=weeks,
        tasks_by_date=tasks_by_date,
        today=today,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        date=date,
    )


if __name__ == "__main__":
    app.run(debug=True)
