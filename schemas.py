from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TimeEntryBase(BaseModel):
    time_allocated_seconds: int

class TimeEntryCreate(TimeEntryBase):
    pass

class TimeEntry(TimeEntryBase):
    id: int
    subprocess_id: int
    start_time: datetime
    stop_time: datetime

    class Config:
        orm_mode = True

class SubprocessBase(BaseModel):
    name: str

class SubprocessCreate(SubprocessBase):
    process_id: int

class Subprocess(SubprocessBase):
    id: int
    process_id: int
    completed: bool
    time_entries: List[TimeEntry] = []

    class Config:
        orm_mode = True

class ProcessBase(BaseModel):
    name: str

class ProcessCreate(ProcessBase):
    pass

class Process(ProcessBase):
    id: int
    subprocesses: List[Subprocess] = []

    class Config:
        orm_mode = True
