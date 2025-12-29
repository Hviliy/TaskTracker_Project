from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from matplotlib import pyplot as plt
from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app.api.deps import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.db.models import User, TaskStatus, Task, Topic, TaskStatusHistory

templates = Jinja2Templates(directory="app/ui/templates")
router = APIRouter(prefix="/ui", tags=["ui"])

def _scope_for_user(user: User):
    if user.role.value == "admin":
        return None
    return Task.creator_id == user.id

def _png_bar(labels, values, title: str) -> StreamingResponse:
    fig = plt.figure()
    plt.title(title)
    plt.bar([str(x) for x in labels], values)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

def _require_admin(request: Request, db: Session) -> User | None:
    user = _get_user_from_cookie(request, db)
    if not user:
        return None
    if user.role.value != "admin":
        return None
    return user

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None, "show_nav": False})

@router.post("/register")
def register_action(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    exists = db.query(User).filter(User.email == email).one_or_none()
    if exists:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Почта уже зарегистрирована", "show_nav": False})

    user = User(name=name, email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))
    resp = RedirectResponse(url="/ui/tasks", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, samesite="lax")
    return resp

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "show_nav": False})


@router.post("/login")
def login_action(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин/пароль"})

    token = create_access_token(subject=str(user.id))
    resp = RedirectResponse(url="/ui/tasks", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, samesite="lax")
    return resp


def _get_user_from_cookie(request: Request, db: Session) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None

    from jose import jwt, JWTError
    from app.core.config import settings

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    statuses = db.query(TaskStatus).order_by(TaskStatus.sort_order.asc()).all()

    q = db.query(Task)
    if user.role.value != "admin":
        q = q.filter(Task.creator_id == user.id)
    tasks = q.order_by(Task.created_at.desc()).limit(200).all()
    topics = db.query(Topic).order_by(Topic.name.asc()).all()
    users = db.query(User).order_by(User.name.asc()).all()

    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "user": user,
            "tasks": tasks,
            "statuses": statuses,
            "topics": topics,
            "users": users,
            "show_nav": True,
        },
    )


@router.post("/tasks")
def create_task_ui(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    description: str | None = Form(None),
    priority: int = Form(3),
    topic_id: str | None = Form(None),
    assignee_id: str | None = Form(None),
):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    status_new = db.query(TaskStatus).filter(TaskStatus.code == "new").one()
    topic_id_int = int(topic_id) if topic_id and topic_id.isdigit() else None
    assignee_id_int = int(assignee_id) if assignee_id and assignee_id.isdigit() else None
    task = Task(
        title=title,
        description=description,
        priority=priority,
        status_id=status_new.id,
        creator_id=user.id,
        topic_id=topic_id_int,
        assignee_id=assignee_id_int,
    )

    db.add(task)
    db.flush()
    return RedirectResponse(url="/ui/tasks", status_code=302)


@router.post("/tasks/{task_id}/status")
def change_status_ui(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    status_code: str = Form(...),
):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    if user.role.value != "admin" and task.creator_id != user.id:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    new_status = db.query(TaskStatus).filter(TaskStatus.code == status_code).one()
    task.status_id = new_status.id
    db.add(task)
    db.flush()
    return RedirectResponse(url="/ui/tasks", status_code=302)

@router.post("/tasks/{task_id}/delete")
def delete_task_ui(request: Request, task_id: int, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    if user.role.value != "admin" and task.creator_id != user.id:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    db.delete(task)
    db.flush()
    return RedirectResponse(url="/ui/tasks", status_code=302)

@router.post("/tasks/{task_id}/update")
def update_task_ui(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    title: str = Form(...),
    description: str | None = Form(None),
    priority: int = Form(3),
    topic_id: str | None = Form(None),
    assignee_id: str | None = Form(None),
):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    if user.role.value != "admin" and task.creator_id != user.id:
        return RedirectResponse(url="/ui/tasks", status_code=302)

    topic_id_int = int(topic_id) if topic_id and topic_id.isdigit() else None
    assignee_id_int = int(assignee_id) if assignee_id and assignee_id.isdigit() else None

    task.title = title.strip()
    task.description = description
    task.priority = priority
    task.topic_id = topic_id_int
    task.assignee_id = assignee_id_int

    db.add(task)
    db.flush()
    return RedirectResponse(url="/ui/tasks", status_code=302)

@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)
    return templates.TemplateResponse("analytics.html", {"request": request})

@router.get("/analytics/statuses.png")
def ui_analytics_statuses_png(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    scope = _scope_for_user(user)
    conds = []
    if scope is not None:
        conds.append(scope)

    join_on = and_(Task.status_id == TaskStatus.id, *conds) if conds else (Task.status_id == TaskStatus.id)

    rows = db.execute(
        select(TaskStatus.name, func.count(Task.id))
        .select_from(TaskStatus)
        .outerjoin(Task, join_on)
        .group_by(TaskStatus.id)
        .order_by(TaskStatus.sort_order.asc())
    ).all()

    labels = [r[0] for r in rows]
    values = [int(r[1]) for r in rows]
    return _png_bar(labels, values, "Задачи по статусам")

@router.get("/analytics/topics.png")
def ui_analytics_topics_png(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    scope = _scope_for_user(user)
    conds = []
    if scope is not None:
        conds.append(scope)

    join_on = and_(Task.topic_id == Topic.id, *conds) if conds else (Task.topic_id == Topic.id)

    rows = db.execute(
        select(Topic.name, func.count(Task.id))
        .select_from(Topic)
        .outerjoin(Task, join_on)
        .group_by(Topic.id)
        .order_by(func.count(Task.id).desc())
    ).all()

    labels = [r[0] for r in rows]
    values = [int(r[1]) for r in rows]
    return _png_bar(labels, values, "Задачи по темам")

@router.get("/analytics/assignees.png")
def ui_analytics_assignees_png(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    scope = _scope_for_user(user)
    stmt = select(
        func.coalesce(User.name, "Без исполнителя").label("assignee"),
        func.count(Task.id).label("count"),
    ).select_from(Task).outerjoin(User, Task.assignee_id == User.id)

    if scope is not None:
        stmt = stmt.where(scope)

    rows = db.execute(
        stmt.group_by("assignee").order_by(func.count(Task.id).desc())
    ).all()

    labels = [r[0] for r in rows]
    values = [int(r[1]) for r in rows]
    return _png_bar(labels, values, "Задачи по исполнителям")

@router.get("/analytics/lead_time.png")
def ui_analytics_lead_time_png(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    scope = _scope_for_user(user)

    done_id = db.execute(select(TaskStatus.id).where(TaskStatus.code == "done")).scalar_one_or_none()
    if not done_id:
        return _png_bar(["done"], [0], "Время выполнения")

    subq = (
        select(
            TaskStatusHistory.task_id.label("task_id"),
            func.min(TaskStatusHistory.changed_at).label("done_at"),
        )
        .where(TaskStatusHistory.to_status_id == done_id)
        .group_by(TaskStatusHistory.task_id)
        .subquery()
    )

    stmt = select(func.extract("epoch", subq.c.done_at - Task.created_at)).select_from(Task).join(subq, subq.c.task_id == Task.id)
    if scope is not None:
        stmt = stmt.where(scope)

    rows = db.execute(stmt).scalars().all()
    secs = pd.to_numeric(pd.Series(rows), errors="coerce").dropna()

    avg_h = float((secs.mean() / 3600)) if len(secs) else 0.0
    return _png_bar(["Часов в среднем"], [round(avg_h, 2)], "Время выполнения до завершения задач")

@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/ui/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse(url="/ui/login", status_code=302)

    users = db.query(User).order_by(User.id.asc()).all()
    topics = db.query(Topic).order_by(Topic.name.asc()).all()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "user": user, "users": users, "topics": topics, "show_nav": True},
    )

@router.post("/admin/users/{user_id}/role")
def admin_change_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = _require_admin(request, db)
    if not admin:
        return RedirectResponse(url="/ui/login", status_code=302)

    u = db.get(User, user_id)
    if not u:
        return RedirectResponse(url="/ui/admin", status_code=302)

    if role not in ("user", "admin"):
        return RedirectResponse(url="/ui/admin", status_code=302)

    u.role = role
    db.add(u)
    db.flush()
    return RedirectResponse(url="/ui/admin", status_code=302)

@router.post("/admin/users/{user_id}/toggle_active")
def admin_toggle_active(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = _require_admin(request, db)
    if not admin:
        return RedirectResponse(url="/ui/login", status_code=302)

    u = db.get(User, user_id)
    if not u:
        return RedirectResponse(url="/ui/admin", status_code=302)

    if u.id == admin.id:
        return RedirectResponse(url="/ui/admin", status_code=302)

    u.is_active = not u.is_active
    db.add(u)
    db.flush()
    return RedirectResponse(url="/ui/admin", status_code=302)

@router.post("/admin/topics/create")
def admin_create_topic(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    admin = _require_admin(request, db)
    if not admin:
        return RedirectResponse(url="/ui/login", status_code=302)

    name = name.strip()
    if not name:
        return RedirectResponse(url="/ui/admin", status_code=302)

    exists = db.query(Topic).filter(Topic.name == name).one_or_none()
    if exists:
        return RedirectResponse(url="/ui/admin", status_code=302)

    topic = Topic(name=name, description=description)
    db.add(topic)
    db.flush()
    return RedirectResponse(url="/ui/admin", status_code=302)

@router.post("/admin/topics/{topic_id}/update")
def admin_update_topic(
    request: Request,
    topic_id: int,
    name: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    admin = _require_admin(request, db)
    if not admin:
        return RedirectResponse(url="/ui/login", status_code=302)

    topic = db.get(Topic, topic_id)
    if not topic:
        return RedirectResponse(url="/ui/admin", status_code=302)

    name = name.strip()
    if not name:
        return RedirectResponse(url="/ui/admin", status_code=302)

    exists = db.query(Topic).filter(Topic.name == name, Topic.id != topic_id).one_or_none()
    if exists:
        return RedirectResponse(url="/ui/admin", status_code=302)

    topic.name = name
    topic.description = description
    db.add(topic)
    db.flush()
    return RedirectResponse(url="/ui/admin", status_code=302)

@router.post("/admin/topics/{topic_id}/delete")
def admin_delete_topic(request: Request, topic_id: int, db: Session = Depends(get_db)):
    admin = _require_admin(request, db)
    if not admin:
        return RedirectResponse(url="/ui/login", status_code=302)

    topic = db.get(Topic, topic_id)
    if not topic:
        return RedirectResponse(url="/ui/admin", status_code=302)

    db.delete(topic)
    db.flush()
    return RedirectResponse(url="/ui/admin", status_code=302)