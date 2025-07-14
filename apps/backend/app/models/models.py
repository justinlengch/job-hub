from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class JobApplication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    company: str
    role: str
    job_posting_url: Optional[str] = None
    application_date: datetime
    status: str
    source: Optional[str] = None
    notes: Optional[str] = None

    timeline_events: List["TimelineEvent"] = Relationship(back_populates="application")
    reminders: List["Reminder"] = Relationship(back_populates="application")

class TimelineEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="jobapplication.id")
    event_type: str
    event_date: datetime
    description: Optional[str] = None

    application: Optional[JobApplication] = Relationship(back_populates="timeline_events")

class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="jobapplication.id")
    remind_at: datetime
    message: str
    completed: bool = False

    application: Optional[JobApplication] = Relationship(back_populates="reminders")