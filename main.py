"""Flask entry point for FocusTrack."""
from collections import defaultdict

from flask import Flask, redirect, render_template, request, url_for

from database import Base, engine, get_session
import models  # noqa: F401  # ensure models register with metadata
from managers import CategoryManager, ReminderManager, TaskManager

app = Flask(__name__)

# global session and managers
session = get_session()
task_manager = TaskManager(session)
category_manager = task_manager.category_manager
reminder_manager = ReminderManager(session)

# create tables once
Base.metadata.create_all(engine)


# route for dashboard
@app.route("/")
@app.route("/dashboard")
def dashboard():
    tasks = task_manager.list_tasks()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "Done")
    in_progress_tasks = sum(1 for t in tasks if t.status == "In Progress")
    pending_tasks = sum(1 for t in tasks if t.status != "Done")
    percent_complete = int((completed_tasks / total_tasks) * 100) if total_tasks else 0
    percent_pending = int((pending_tasks / total_tasks) * 100) if total_tasks else 0
    percent_in_progress = int((in_progress_tasks / total_tasks) * 100) if total_tasks else 0

    def sort_key(task):
        return task.due_date or "9999-12-31"

    upcoming = sorted(tasks, key=sort_key)[:5]
    recent_tasks = sorted(tasks, key=lambda t: t.created_at or "", reverse=True)[:5]

    # counts for priority legend
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


# route for tasks list and form
@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        # handle new task submission
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        status = request.form.get("status")
        category_name = request.form.get("category_name")
        try:
            task_manager.create_task(title, description, due_date, priority, status, category_name)
        except Exception:
            pass  # keep simple; in class demos we just skip errors
        return redirect(url_for("tasks"))

    tasks_list = task_manager.list_tasks()
    categories = category_manager.list_categories()
    return render_template(
        "tasks.html",
        active_page="tasks",
        tasks=tasks_list,
        categories=categories,
        priorities=TaskManager.VALID_PRIORITIES,
        statuses=TaskManager.VALID_STATUS,
    )


# mark task done
@app.route("/tasks/<int:task_id>/done", methods=["POST"])
def mark_done(task_id):
    task_manager.update_task_status(task_id, "Done")
    return redirect(url_for("tasks"))


# delete task
@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    task_manager.delete_task(task_id)
    return redirect(url_for("tasks"))


# calendar view
@app.route("/calendar")
def calendar():
    grouped = defaultdict(list)
    for task in task_manager.list_tasks():
        key = task.due_date or "No due date"
        grouped[key].append(task)
    grouped_tasks = dict(sorted(grouped.items()))
    return render_template(
        "calendar.html",
        active_page="calendar",
        grouped_tasks=grouped_tasks,
    )


if __name__ == "__main__":
    app.run(debug=True)
