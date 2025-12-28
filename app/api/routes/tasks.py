from typing import Literal

from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlalchemy import select, asc, desc
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Task
from app.schemas.task import TaskOut, TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    try:
        task = Task(
            title=payload.title,
            description=payload.description,
            topic_id=payload.topic_id,
            assignee_id=payload.assignee_id,
            priority=payload.priority,
            due_date=payload.due_date,
            status_id=1,
            creator_id=1,
        )
        db.add(task)
        db.flush()
        db.refresh(task)
        return task
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Create failed: {e}")

@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    status_id: int | None = None,
    topic_id: int | None = None,
    assignee_id: int | None = None,
    sort_by: Literal["created_at", "due_date", "priority"] = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Task]:
    stmt = select(Task)

    if status_id is not None:
        stmt = stmt.where(Task.status_id == status_id)
    if topic_id is not None:
        stmt = stmt.where(Task.topic_id == topic_id)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    order_col = getattr(Task, sort_by)
    stmt = stmt.order_by(asc(order_col) if sort_dir == "asc" else desc(order_col))
    stmt = stmt.limit(limit).offset(offset)

    return list(db.execute(stmt).scalars().all())

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> type[Task]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> type[Task]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(task, k, v)
        db.add(task)
        db.flush()
        db.refresh(task)
        return task
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {e}")

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        db.delete(task)
        db.flush()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Delete failed: {e}")