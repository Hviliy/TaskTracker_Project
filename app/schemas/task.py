from datetime import date, datetime

from fastapi import Form, HTTPException
from pydantic import BaseModel, Field, ValidationError, ConfigDict


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    topic_id: int | None = Field(default=None, gt=0)
    assignee_id: int | None = Field(default=None, gt=0)
    priority: int = Field(default=3, ge=1, le=5)
    due_date: date | None = None

    @classmethod
    def as_form(
            cls,
            title: str = Form(...),
            description: str | None = Form(None),
            topic_id: int | None = Form(None),
            assignee_id: int | None = Form(None),
            priority: int = Form(3),
            due_date: date | None = Form(None),
    ) -> "TaskCreate":
        try:
            if topic_id == 0:
                topic_id = None
            if assignee_id == 0:
                assignee_id = None
            return cls(
                title=title,
                description=description,
                topic_id=topic_id,
                assignee_id=assignee_id,
                priority=priority,
                due_date=due_date,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    topic_id: int | None = Field(default=None, gt=0)
    assignee_id: int | None = Field(default=None, gt=0)
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None

    @classmethod
    def as_form(
            cls,
            title: str | None = Form(None),
            description: str | None = Form(None),
            topic_id: int | None = Form(None),
            assignee_id: int | None = Form(None),
            priority: int | None = Form(None),
            due_date: date | None = Form(None),
    ) -> "TaskUpdate":
        try:
            if topic_id == 0:
                topic_id = None
            if assignee_id == 0:
                assignee_id = None
            if priority == 0:
                priority = None
            return cls(
                title=title,
                description=description,
                topic_id=topic_id,
                assignee_id=assignee_id,
                priority=priority,
                due_date=due_date,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


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

    model_config = ConfigDict(from_attributes=True)