from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

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

class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    subprocess_id = Column(Integer, ForeignKey("subprocesses.id"))
    time_allocated_seconds = Column(Integer)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    stop_time = Column(DateTime, default=datetime.datetime.utcnow)

    subprocess = relationship("Subprocess", back_populates="time_entries")
