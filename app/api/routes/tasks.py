from typing import Literal

from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlalchemy import select, asc, desc
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models import Task, User, UserRole, Topic, TaskStatus, TaskStatusHistory
from app.schemas.task import TaskOut, TaskCreate, TaskUpdate
from app.schemas.task_status import TaskStatusChange

router = APIRouter(prefix="/tasks", tags=["Задачи"])

def _check_task_access(task: Task, user: User) -> None:
    if user.role == UserRole.admin:
        return
    if task.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="Создать задачу")
def create_task(
    payload: TaskCreate = Depends(TaskCreate.as_form),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        topic_id=payload.topic_id,
        assignee_id=payload.assignee_id,
        priority=payload.priority,
        due_date=payload.due_date,
        status_id=1,
        creator_id=user.id
    )
    if payload.topic_id is not None and not db.get(Topic, payload.topic_id):
        raise HTTPException(status_code=400, detail="Тема не найдена")
    if payload.assignee_id is not None and not db.get(User, payload.assignee_id):
        raise HTTPException(status_code=400, detail="Исполнитель не найден")
    db.add(task)
    db.flush()
    db.refresh(task)
    return task

@router.get("", response_model=list[TaskOut], summary="Открыть список задач")
def list_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_id: int | None = None,
    topic_id: int | None = None,
    assignee_id: int | None = None,
    sort_by: Literal["created_at", "due_date", "priority", "title"] = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Task]:
    stmt = select(Task)

    if user.role != UserRole.admin:
        stmt = stmt.where(Task.creator_id == user.id)

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



@router.get("/{task_id}", response_model=TaskOut, summary="Получить задачу")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    _check_task_access(task, user)
    return task

@router.patch("/{task_id}", response_model=TaskOut, summary="Обновить задачу")
def update_task(
    task_id: int,
    payload: TaskUpdate = Depends(TaskUpdate.as_form),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    _check_task_access(task, user)

    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(task, k, v)

    db.add(task)
    db.flush()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить задачу")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    _check_task_access(task, user)

    db.delete(task)
    db.flush()

@router.patch("/{task_id}/status", response_model=TaskOut, summary="Изменить статус задачи")
def change_task_status(
    task_id: int,
    payload: TaskStatusChange= Depends(TaskStatusChange.as_form),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    _check_task_access(task, user)

    new_status = db.execute(
        select(TaskStatus).where(TaskStatus.code == payload.status_code)
    ).scalar_one_or_none()
    if not new_status:
        raise HTTPException(status_code=400, detail="Неизвестный статус")

    if task.status_id == new_status.id:
        return task

    old_status_id = task.status_id
    task.status_id = new_status.id

    history = TaskStatusHistory(
        task_id=task.id,
        from_status_id=old_status_id,
        to_status_id=new_status.id,
        changed_by_id=user.id,
    )
    db.add(history)

    db.add(task)
    db.flush()
    db.refresh(task)
    return task