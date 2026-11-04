from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import datetime

task_users_table = Table(
    "task_users",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
)


class TaskSubprocessCompletion(Base):
    __tablename__ = "task_subprocess_completions"
    __table_args__ = (
        UniqueConstraint("task_id", "subprocess_id", name="uq_task_subprocess"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    subprocess_id = Column(Integer, ForeignKey("subprocesses.id", ondelete="CASCADE"), nullable=False, index=True)
    completed = Column(Boolean, default=True, nullable=False)

    task = relationship("Task", back_populates="subprocess_completions")
    subprocess = relationship("Subprocess")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    time_entries = relationship("TimeEntry", back_populates="user")
    assigned_tasks = relationship("Task", secondary=task_users_table, back_populates="users")


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    subprocesses = relationship("Subprocess", back_populates="process", cascade="all, delete-orphan")


class Subprocess(Base):
    __tablename__ = "subprocesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    process_id = Column(Integer, ForeignKey("processes.id", ondelete="CASCADE"))
    completed = Column(Boolean, default=False)

    process = relationship("Process", back_populates="subprocesses")
    time_entries = relationship("TimeEntry", back_populates="subprocess", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    numeric_id = Column(Integer, unique=True, index=True)  # Ticket ID
    name = Column(String, index=True)
    process_id = Column(Integer, ForeignKey("processes.id", ondelete="SET NULL"))
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    process = relationship("Process")
    users = relationship("User", secondary=task_users_table, back_populates="assigned_tasks")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")
    subprocess_completions = relationship(
        "TaskSubprocessCompletion",
        back_populates="task",
        cascade="all, delete-orphan"
    )

    @property
    def completed_subprocess_ids(self) -> list[int]:
        return [sc.subprocess_id for sc in self.subprocess_completions if sc.completed]


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    subprocess_id = Column(Integer, ForeignKey("subprocesses.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    time_allocated_seconds = Column(Integer, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.now)
    stop_time = Column(DateTime, default=datetime.datetime.now)

    task = relationship("Task", back_populates="time_entries")
    subprocess = relationship("Subprocess", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")
