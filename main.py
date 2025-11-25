from collections import defaultdict
from datetime import date, datetime
import calendar

from flask import Flask, redirect, render_template, request, url_for

from database import Base, engine, get_session
import models
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
    # count tasks by status
    completed_tasks = sum(1 for t in tasks if t.status == "Done")
    in_progress_tasks = sum(1 for t in tasks if t.status == "In Progress")
    pending_tasks = sum(1 for t in tasks if t.status == "Pending")

    # compute percentages for progress bar
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


# edit task
@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return redirect(url_for("tasks"))

    if request.method == "POST":
        # handle edit form submission
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        status = request.form.get("status") or task.status
        category_name = request.form.get("category_name")
        try:
            task_manager.update_task(task_id, title, description, due_date, priority, status, category_name)
        except Exception:
            pass
        return redirect(url_for("tasks"))

    # show edit form
    categories = category_manager.list_categories()
    return render_template(
        "edit_task.html",
        active_page="tasks",
        task=task,
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
@app.route("/calendar", endpoint="calendar")
def calendar_view():
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    # build month matrix
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    # group tasks by due date
    tasks_by_date = {}
    for task in task_manager.list_tasks():
        if task.due_date:
            try:
                d = datetime.strptime(task.due_date, "%Y-%m-%d").date()
                tasks_by_date.setdefault(d, []).append(task)
            except Exception:
                pass

    # compute previous and next month
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
