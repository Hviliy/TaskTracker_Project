from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user, require_admin
from app.db.models import Topic, User
from app.schemas.topic import TopicCreate, TopicOut, TopicUpdate

router = APIRouter(prefix="/topics", tags=["Темы"])

@router.get("", response_model=list[TopicOut], summary="Список тем")
def list_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.execute(select(Topic).order_by(Topic.name.asc())).scalars().all())

@router.post("",
             response_model=TopicOut,
             status_code=status.HTTP_201_CREATED,
             summary="Создать тему(только для Админа)")
def create_topic(payload: TopicCreate = Depends(TopicCreate.as_form), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    exists = db.execute(select(Topic).where(Topic.name == payload.name)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Тема уже существует")

    topic = Topic(name=payload.name, description=payload.description)
    db.add(topic)
    db.flush()
    db.refresh(topic)
    return topic

@router.patch("/{topic_id}", response_model=TopicOut, summary="Обновить тему(только для Админа)")
def update_topic(topic_id: int, payload: TopicUpdate = Depends(TopicUpdate.as_form), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(topic, k, v)

    db.add(topic)
    db.flush()
    db.refresh(topic)
    return topic

@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить тему(только для Админа)")
def delete_topic(topic_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    db.delete(topic)
    db.flush()