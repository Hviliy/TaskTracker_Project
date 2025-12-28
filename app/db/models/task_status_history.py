from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    # может быть null для первой установки статуса
    from_status_id: Mapped[int | None] = mapped_column(ForeignKey("task_statuses.id", ondelete="SET NULL"),
                                                       nullable=True)
    to_status_id: Mapped[int] = mapped_column(ForeignKey("task_statuses.id", ondelete="RESTRICT"),
                                              nullable=False)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"),
                                               nullable=False, index=True)
    changed_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("Task", back_populates="history")
    changed_by = relationship("User", back_populates="status_changes", foreign_keys=[changed_by_id])
    # две связи на одну таблицу статусов
    from_status = relationship("TaskStatus", foreign_keys=[from_status_id])
    to_status = relationship("TaskStatus", foreign_keys=[to_status_id])