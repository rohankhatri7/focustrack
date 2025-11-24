"""Managers hide database work from the Flask routes."""
from datetime import datetime

from sqlalchemy import select

from models import Category, Reminder, Task


class BaseManager:
    def __init__(self, session):
        self.session = session

    def get_model_class(self):
        return None

    def list_all(self):
        model = self.get_model_class()
        if not model:
            return []
        stmt = select(model)
        return self.session.execute(stmt).scalars().all()

    def _commit(self):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise


class CategoryManager(BaseManager):
    def get_model_class(self):
        return Category

    def get_or_create_category(self, name):
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        stmt = select(Category).where(Category.name == cleaned)
        category = self.session.execute(stmt).scalar_one_or_none()
        if category:
            return category
        category = Category(name=cleaned)
        self.session.add(category)
        self._commit()
        return category

    def list_categories(self):
        return self.list_all()


class TaskManager(BaseManager):
    VALID_PRIORITIES = ["Low", "Medium", "High"]
    VALID_STATUS = ["Pending", "In Progress", "Done"]

    def __init__(self, session, category_manager=None):
        super().__init__(session)
        self.category_manager = category_manager or CategoryManager(session)

    def get_model_class(self):
        return Task

    def create_task(self, title, description, due_date, priority, status, category_name):
        if not title:
            raise ValueError("Title is required")
        if priority not in self.VALID_PRIORITIES:
            raise ValueError("Invalid priority")
        if status not in self.VALID_STATUS:
            raise ValueError("Invalid status")

        category = self.category_manager.get_or_create_category(category_name) if category_name else None
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        task = Task(
            title=title.strip(),
            description=(description or "").strip(),
            due_date=(due_date or "").strip(),
            priority=priority,
            status=status,
            created_at=created_at,
            category_id=category.id if category else None,
        )
        self.session.add(task)
        self._commit()
        return task

    def list_tasks(self, status=None):
        stmt = select(Task)
        if status and status in self.VALID_STATUS:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.due_date)
        tasks = self.session.execute(stmt).scalars().all()
        # touch relationships while session open
        for task in tasks:
            _ = task.category.name if task.category else None
        return tasks

    def get_task(self, task_id):
        return self.session.get(Task, task_id)

    def update_task_status(self, task_id, new_status):
        if new_status not in self.VALID_STATUS:
            raise ValueError("Invalid status")
        task = self.session.get(Task, task_id)
        if not task:
            return False
        task.status = new_status
        self._commit()
        return True

    def delete_task(self, task_id):
        task = self.session.get(Task, task_id)
        if not task:
            return False
        self.session.delete(task)
        self._commit()
        return True


class ReminderManager(BaseManager):
    def get_model_class(self):
        return Reminder

    def create_reminder(self, task_id, remind_at):
        if not remind_at:
            raise ValueError("remind_at required")
        reminder = Reminder(task_id=task_id, remind_at=remind_at)
        self.session.add(reminder)
        self._commit()
        return reminder

    def list_reminders_for_task(self, task_id):
        stmt = select(Reminder).where(Reminder.task_id == task_id)
        return self.session.execute(stmt).scalars().all()
