"""ORM models for FocusTrack."""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

    def summary(self):
        return f"{self.__class__.__name__}#{self.id}"

    def to_dict(self):
        # build a plain dict for UI use
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return f"<{self.summary()}>"


class Category(BaseModel):
    __tablename__ = "categories"

    name = Column(String, unique=True, nullable=False)

    tasks = relationship("Task", back_populates="category")

    def summary(self):
        return f"Category#{self.id}:{self.name}"


class Task(BaseModel):
    __tablename__ = "tasks"

    title = Column(String, nullable=False)
    description = Column(String)
    due_date = Column(String)
    priority = Column(String)
    status = Column(String)
    created_at = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))

    category = relationship("Category", back_populates="tasks")
    reminders = relationship(
        "Reminder",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    def summary(self):
        return f"Task#{self.id}:{self.title} due {self.due_date or 'n/a'}"


class Reminder(BaseModel):
    __tablename__ = "reminders"

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    remind_at = Column(String, nullable=False)

    task = relationship("Task", back_populates="reminders")

    def summary(self):
        return f"Reminder#{self.id} for Task {self.task_id}"
