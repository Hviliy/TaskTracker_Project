from datetime import date, datetime
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    topic_id: int | None = None
    assignee_id: int | None = None
    priority: int = Field(default=3, ge=1, le=5)
    due_date: date | None = None

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    topic_id: int | None = None
    assignee_id: int | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    status_id: int
    topic_id: int | None
    creator_id: int
    assignee_id: int | None
    priority: int
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True