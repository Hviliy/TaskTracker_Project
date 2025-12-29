import enum
from sqlalchemy import String, Boolean, DateTime, Enum, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        server_default=text("'user'"),
        default=UserRole.user
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # две связи на tasks: создал и назначен
    created_tasks = relationship(
        "Task",
        back_populates="creator",
        foreign_keys="Task.creator_id"
    )
    assigned_tasks = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assignee_id"
    )
    # кто менял статусы
    status_changes = relationship(
        "TaskStatusHistory",
        back_populates="changed_by",
        foreign_keys="TaskStatusHistory.changed_by_id"
    )