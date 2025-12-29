from datetime import date, timedelta
from io import BytesIO
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models import UserRole, Task, User, TaskStatus, Topic, TaskStatusHistory

router = APIRouter(prefix="/analytics", tags=["Аналитика"])

# ограничение видимости данных
def _task_scope_filter(user: User):
    if user.role == UserRole.admin:
        return None
    return Task.creator_id == user.id

# рисует столбчатую диаграмму и отдаёт как png
def _df_to_png_bar(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> StreamingResponse:
    fig = plt.figure()
    plt.title(title)
    plt.bar(df[x_col].astype(str), df[y_col])
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

# линейная диаграмма
def _df_to_png_line(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> StreamingResponse:
    fig = plt.figure()
    plt.title(title)
    plt.plot(df[x_col], df[y_col], marker="o")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# гистограмма
def _series_to_png_hist(values: pd.Series, title: str, bins: int = 20) -> StreamingResponse:
    fig = plt.figure()
    plt.title(title)
    plt.hist(values.dropna(), bins=bins)
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/statuses", summary="Аналитика по статусам")
def analytics_by_statuses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    format: Literal["json", "png"] = "json",
    date_from: date | None = None,
    date_to: date | None = None,
):
    scope = _task_scope_filter(user)

    conds = []
    if scope is not None:
        conds.append(scope)
    if date_from:
        conds.append(Task.created_at >= date_from)
    if date_to:
        conds.append(Task.created_at < date_to)

    join_on = and_(Task.status_id == TaskStatus.id, *conds) if conds else (Task.status_id == TaskStatus.id)

    stmt = (
        select(
            TaskStatus.code.label("code"),
            TaskStatus.name.label("name"),
            func.count(Task.id).label("count"),
        )
        .select_from(TaskStatus)
        .outerjoin(Task, join_on)
        .group_by(TaskStatus.id)
        .order_by(TaskStatus.sort_order.asc())
    )

    rows = db.execute(stmt).mappings().all()
    df = pd.DataFrame(rows)

    if df.empty:
        raise HTTPException(status_code=404, detail="Нет данных")

    total = int(df["count"].sum())
    df["percent"] = (df["count"] / total * 100).round(1) if total else 0.0

    if format == "png":
        return _df_to_png_bar(df, x_col="name", y_col="count", title="Задачи по статусам")

    return {
        "total": total,
        "items": df.to_dict(orient="records"),
    }

@router.get("/topics", summary="Аналитика по темам")
def analytics_by_topics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    format: Literal["json", "png"] = "json",
):
    scope = _task_scope_filter(user)

    conds = []
    if scope is not None:
        conds.append(scope)

    join_on = and_(Task.topic_id == Topic.id, *conds) if conds else (Task.topic_id == Topic.id)

    stmt = (
        select(
            Topic.name.label("topic"),
            func.count(Task.id).label("count"),
        )
        .select_from(Topic)
        .outerjoin(Task, join_on)
        .group_by(Topic.id)
        .order_by(func.count(Task.id).desc())
    )

    rows = db.execute(stmt).mappings().all()
    df = pd.DataFrame(rows)

    if df.empty:
        raise HTTPException(status_code=404, detail="Нет данных")

    total = int(df["count"].sum())
    df["percent"] = (df["count"] / total * 100).round(1) if total else 0.0

    if format == "png":
        return _df_to_png_bar(df, x_col="topic", y_col="count", title="Задачи по темам")

    return {"total": total, "items": df.to_dict(orient="records")}

@router.get("/assignees", summary="Аналитика по исполнителям")
def analytics_by_assignees(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    format: Literal["json", "png"] = "json",
    include_unassigned: bool = Query(default=True),
):
    scope = _task_scope_filter(user)

    conds = []
    if scope is not None:
        conds.append(scope)

    join_on = and_(Task.assignee_id == User.id, *conds) if conds else (Task.assignee_id == User.id)

    stmt = (
        select(
            User.name.label("assignee"),
            func.count(Task.id).label("count"),
        )
        .select_from(User)
        .outerjoin(Task, join_on)
        .group_by(User.id)
        .order_by(func.count(Task.id).desc())
    )

    rows = db.execute(stmt).mappings().all()
    df = pd.DataFrame(rows)

    if include_unassigned:
        stmt_unassigned = select(func.count(Task.id)).where(Task.assignee_id.is_(None))
        if scope is not None:
            stmt_unassigned = stmt_unassigned.where(scope)
        unassigned_count = int(db.execute(stmt_unassigned).scalar_one())
        if unassigned_count > 0:
            df = pd.concat([df, pd.DataFrame(
                [{"assignee": "Без исполнителя", "count": unassigned_count}])],
                           ignore_index=True)

    if df.empty:
        raise HTTPException(status_code=404, detail="Нет данных")

    total = int(df["count"].sum())
    df["percent"] = (df["count"] / total * 100).round(1) if total else 0.0

    if format == "png":
        return _df_to_png_bar(df, x_col="assignee", y_col="count", title="Задачи по исполнителям")

    return {"total": total, "items": df.to_dict(orient="records")}


@router.get("/summary", summary="Сводка")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scope = _task_scope_filter(user)

    done_status_id = db.execute(
        select(TaskStatus.id).where(TaskStatus.code == "done")
    ).scalar_one_or_none()
    if not done_status_id:
        raise HTTPException(status_code=500, detail="Статус 'Сделано' не найден")

    today = date.today()
    week_ago = today - timedelta(days=7)

    base = select(func.count(Task.id))
    base_open = select(func.count(Task.id)).where(Task.status_id != done_status_id)
    base_done = select(func.count(Task.id)).where(Task.status_id == done_status_id)

    if scope is not None:
        base = base.where(scope)
        base_open = base_open.where(scope)
        base_done = base_done.where(scope)

    total = int(db.execute(base).scalar_one())
    open_cnt = int(db.execute(base_open).scalar_one())
    done_cnt = int(db.execute(base_done).scalar_one())

    overdue_stmt = select(func.count(Task.id)).where(
        Task.due_date.is_not(None),
        Task.due_date < today,
        Task.status_id != done_status_id,
    )
    if scope is not None:
        overdue_stmt = overdue_stmt.where(scope)
    overdue = int(db.execute(overdue_stmt).scalar_one())

    created_7_stmt = select(func.count(Task.id)).where(Task.created_at >= week_ago)
    if scope is not None:
        created_7_stmt = created_7_stmt.where(scope)
    created_last_7 = int(db.execute(created_7_stmt).scalar_one())

    return {
        "total": total,
        "open": open_cnt,
        "done": done_cnt,
        "overdue": overdue,
        "created_last_7_days": created_last_7,
    }


@router.get("/burndown", summary="Диаграмма сгорания задач")
def analytics_burndown(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    format: Literal["json", "png"] = "json",
    date_from: date | None = None,
    date_to: date | None = None,
):
    scope = _task_scope_filter(user)

    done_status_id = db.execute(
        select(TaskStatus.id).where(TaskStatus.code == "done")
    ).scalar_one_or_none()
    if not done_status_id:
        raise HTTPException(status_code=500, detail="Статус 'Сделано' не найден")

    subq = (
        select(
            TaskStatusHistory.task_id.label("task_id"),
            func.min(TaskStatusHistory.changed_at).label("done_at"),
        )
        .where(TaskStatusHistory.to_status_id == done_status_id)
        .group_by(TaskStatusHistory.task_id)
        .subquery()
    )

    stmt = (
        select(
            func.date(subq.c.done_at).label("day"),
            func.count(subq.c.task_id).label("done_count"),
        )
        .select_from(subq)
        .join(Task, Task.id == subq.c.task_id)
        .group_by(func.date(subq.c.done_at))
        .order_by(func.date(subq.c.done_at).asc())
    )

    if scope is not None:
        stmt = stmt.where(scope)
    if date_from:
        stmt = stmt.where(func.date(subq.c.done_at) >= date_from)
    if date_to:
        stmt = stmt.where(func.date(subq.c.done_at) < date_to)

    rows = db.execute(stmt).mappings().all()
    df = pd.DataFrame(rows)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data")

    df["day"] = pd.to_datetime(df["day"])
    if format == "png":
        return _df_to_png_line(df, x_col="day", y_col="done_count", title="Закрытые задачи по дням")

    return {"items": df.assign(day=df["day"].dt.date.astype(str)).to_dict(orient="records")}


@router.get("/lead_time", summary="Аналитика времени выполнения")
def analytics_lead_time(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    format: Literal["json", "png"] = "json",
):
    scope = _task_scope_filter(user)

    done_status_id = db.execute(
        select(TaskStatus.id).where(TaskStatus.code == "done")
    ).scalar_one_or_none()
    if not done_status_id:
        raise HTTPException(status_code=500, detail="Статус 'Сделано' не найден")

    subq = (
        select(
            TaskStatusHistory.task_id.label("task_id"),
            func.min(TaskStatusHistory.changed_at).label("done_at"),
        )
        .where(TaskStatusHistory.to_status_id == done_status_id)
        .group_by(TaskStatusHistory.task_id)
        .subquery()
    )

    stmt = (
        select(
            Task.id.label("task_id"),
            Task.created_at.label("created_at"),
            subq.c.done_at.label("done_at"),
            func.extract("epoch", subq.c.done_at - Task.created_at).label("lead_seconds"),
        )
        .select_from(Task)
        .join(subq, Task.id == subq.c.task_id)
    )
    if scope is not None:
        stmt = stmt.where(scope)

    rows = db.execute(stmt).mappings().all()
    df = pd.DataFrame(rows)
    if df.empty:
        raise HTTPException(status_code=404, detail="Нет данных")

    df["lead_seconds"] = pd.to_numeric(df["lead_seconds"], errors="coerce")
    df = df.dropna(subset=["lead_seconds"])

    if df.empty:
        raise HTTPException(status_code=404, detail="Нет данных")

    df["lead_hours"] = (df["lead_seconds"] / 3600).round(2)

    if format == "png":
        return _series_to_png_hist(df["lead_hours"], title="Распределение времени до конца (часы)", bins=20)

    return {
        "count": int(len(df)),
        "avg_hours": float(df["lead_hours"].mean()),
        "median_hours": float(df["lead_hours"].median()),
        "p90_hours": float(df["lead_hours"].quantile(0.9)),
    }