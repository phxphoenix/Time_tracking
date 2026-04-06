from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.orm import relationship
from database import Base
import datetime

task_users_table = Table(
    "task_users",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("subprocess_id", Integer, ForeignKey("subprocesses.id"))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    time_entries = relationship("TimeEntry", back_populates="user")
    assigned_tasks = relationship("Subprocess", secondary=task_users_table, back_populates="users")


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    subprocesses = relationship("Subprocess", back_populates="process", cascade="all, delete-orphan")


class Subprocess(Base):
    __tablename__ = "subprocesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"))
    completed = Column(Boolean, default=False)
    
    process = relationship("Process", back_populates="subprocesses")
    time_entries = relationship("TimeEntry", back_populates="subprocess", cascade="all, delete-orphan")
    users = relationship("User", secondary=task_users_table, back_populates="assigned_tasks")


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    subprocess_id = Column(Integer, ForeignKey("subprocesses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    time_allocated_seconds = Column(Integer)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    stop_time = Column(DateTime, default=datetime.datetime.utcnow)

    subprocess = relationship("Subprocess", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")
