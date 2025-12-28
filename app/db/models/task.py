from sqlalchemy import String, Text, SmallInteger, Date, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # нельзя удалить статус, если есть задачи с ним
    status_id: Mapped[int] = mapped_column(ForeignKey("task_statuses.id", ondelete="RESTRICT"),
                                           nullable=False, index=True)
    # при удалении темы задача остаётся, но без темы
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"),
                                                 nullable=True, index=True)

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"),
                                            nullable=False, index=True)
    # при удалении исполнителя задача “отвязывается”
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                    nullable=True, index=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("3"), default=3)
    due_date: Mapped["Date | None"] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True),
                                                   server_default=func.now(),
                                                   onupdate=func.now(),
                                                   nullable=False)

    # orm связи
    status = relationship("TaskStatus", back_populates="tasks")
    topic = relationship("Topic", back_populates="tasks")
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    # История статусов удалится вместе с задачей
    history = relationship("TaskStatusHistory", back_populates="task", cascade="all, delete-orphan")