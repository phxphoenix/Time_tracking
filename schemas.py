from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserUpdateOptions(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class User(UserBase):
    id: int
    class Config:
        from_attributes = True
        orm_mode = True

class TimeEntryBase(BaseModel):
    time_allocated_seconds: int

class TimeEntryCreate(TimeEntryBase):
    pass

class TimeEntry(TimeEntryBase):
    id: int
    subprocess_id: int
    user_id: int
    user: Optional[User] = None
    start_time: datetime
    stop_time: datetime

    class Config:
        from_attributes = True
        orm_mode = True

class SubprocessBase(BaseModel):
    name: str

class SubprocessCreate(SubprocessBase):
    process_id: int

class Subprocess(SubprocessBase):
    id: int
    process_id: int
    completed: bool
    users: List[User] = []
    time_entries: List[TimeEntry] = []

    class Config:
        from_attributes = True
        orm_mode = True

class ProcessBase(BaseModel):
    name: str

class ProcessCreate(ProcessBase):
    pass

class Process(ProcessBase):
    id: int
    subprocesses: List[Subprocess] = []

    class Config:
        from_attributes = True
        orm_mode = True
