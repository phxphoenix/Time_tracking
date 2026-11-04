from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    username: str
    email: Optional[str] = ""


class UserCreate(UserBase):
    password: str


class UserUpdateOptions(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TimeEntryBase(BaseModel):
    time_allocated_seconds: int


class TimeEntryCreate(TimeEntryBase):
    task_id: int
    subprocess_id: int


class TimeEntryBrief(TimeEntryBase):
    id: int
    task_id: Optional[int] = None
    subprocess_id: Optional[int] = None
    user_id: Optional[int] = None
    user: Optional[User] = None
    start_time: datetime
    stop_time: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeEntryDetail(BaseModel):
    id: int
    task_id: Optional[int] = None
    task_numeric_id: Optional[int] = None
    task_name: str
    process_id: Optional[int] = None
    process_name: str
    subprocess_id: Optional[int] = None
    subprocess_name: str
    user_id: Optional[int] = None
    username: str
    time_allocated_seconds: int
    start_time: datetime
    stop_time: datetime


class TaskBase(BaseModel):
    numeric_id: int
    name: str
    process_id: Optional[int] = None


class TaskCreate(TaskBase):
    user_ids: List[int] = []


class TaskUpdate(BaseModel):
    numeric_id: Optional[int] = None
    name: Optional[str] = None
    completed: Optional[bool] = None
    user_ids: Optional[List[int]] = None
    process_id: Optional[int] = None


class Task(TaskBase):
    id: int
    completed: bool
    created_at: datetime
    users: List[User] = []
    time_entries: List[TimeEntryBrief] = []
    completed_subprocess_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)


class TimeEntry(TimeEntryBase):
    id: int
    task_id: Optional[int] = None
    subprocess_id: Optional[int] = None
    user_id: Optional[int] = None
    user: Optional[User] = None
    start_time: datetime
    stop_time: datetime

    model_config = ConfigDict(from_attributes=True)


class SubprocessBase(BaseModel):
    name: str


class SubprocessCreate(SubprocessBase):
    process_id: int


class SubprocessUpdate(BaseModel):
    name: str


class Subprocess(SubprocessBase):
    id: int
    process_id: int
    completed: bool
    time_entries: List[TimeEntryBrief] = []

    model_config = ConfigDict(from_attributes=True)


class ProcessBase(BaseModel):
    name: str


class ProcessCreate(ProcessBase):
    pass


class Process(ProcessBase):
    id: int
    subprocesses: List[Subprocess] = []

    model_config = ConfigDict(from_attributes=True)
