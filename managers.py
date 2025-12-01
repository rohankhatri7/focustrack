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
        # don't repeat rollback/commit
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

class CategoryManager(BaseManager):
    def get_model_class(self):
        return Category

    def get_or_create_category(self, name):
        # reuse categories by name; create if not there
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

    def create_task(self, title, description, due_date, priority, status, category_name, user_id=None):
        if not title:
            raise ValueError("Title is required")
        if priority not in self.VALID_PRIORITIES:
            raise ValueError("Invalid priority")
        if status not in self.VALID_STATUS:
            raise ValueError("Invalid status")
        if not user_id:
            raise ValueError("user_id required")

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
            user_id=user_id,
        )
        self.session.add(task)
        self._commit()
        return task

    def list_tasks(self, status=None, user_id=None):
        stmt = select(Task)
        if status and status in self.VALID_STATUS:
            stmt = stmt.where(Task.status == status)
        if user_id:
            stmt = stmt.where(Task.user_id == user_id)
        stmt = stmt.order_by(Task.due_date)
        return self.session.execute(stmt).scalars().all()

    def get_task(self, task_id, user_id=None):
        # make sure the task belongs to the user if user_id provided
        task = self.session.get(Task, task_id)
        if user_id and task and task.user_id != user_id:
            return None
        return task

    def update_task_status(self, task_id, new_status, user_id=None):
        if new_status not in self.VALID_STATUS:
            raise ValueError("Invalid status")
        task = self.get_task(task_id, user_id=user_id)
        if not task:
            return False
        task.status = new_status
        self._commit()
        return True

    def delete_task(self, task_id, user_id=None):
        # only allow users to delete what belongs to them
        task = self.get_task(task_id, user_id=user_id)
        if not task:
            return False
        self.session.delete(task)
        self._commit()
        return True

    def update_task(self, task_id, title, description, due_date, priority, status, category_name, user_id=None):
        task = self.get_task(task_id, user_id=user_id)
        if not task:
            return None
        if not title:
            raise ValueError("Title is required")
        if priority not in self.VALID_PRIORITIES:
            raise ValueError("Invalid priority")
        if status not in self.VALID_STATUS:
            raise ValueError("Invalid status")

        category = self.category_manager.get_or_create_category(category_name) if category_name else None

        task.title = title.strip()
        task.description = (description or "").strip()
        task.due_date = (due_date or "").strip()
        task.priority = priority
        task.status = status
        task.category_id = category.id if category else None

        self._commit()
        return task

class ReminderManager(BaseManager):
    def get_model_class(self):
        return Reminder

    def create_reminder(self, task_id, remind_at):
        # not used much yet, but keeps reminders consistent
        if not remind_at:
            raise ValueError("remind_at required")
        reminder = Reminder(task_id=task_id, remind_at=remind_at)
        self.session.add(reminder)
        self._commit()
        return reminder

    def list_reminders_for_task(self, task_id):
        stmt = select(Reminder).where(Reminder.task_id == task_id)
        return self.session.execute(stmt).scalars().all()
