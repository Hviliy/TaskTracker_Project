from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user, require_admin
from app.db.models import User, UserRole
from app.schemas.user import UserOut, UserRoleUpdate
from app.core.config import settings

router = APIRouter(prefix="/users", tags=["Пользователи"])

@router.get("/me", response_model=UserOut, summary="Профиль")
def me(user: User = Depends(get_current_user)):
    return user

@router.get("", response_model=list[UserOut], summary="Список пользователей(только для Админа)")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return list(db.execute(select(User).order_by(User.id.asc())).scalars().all())

@router.patch("/{user_id}/role", response_model=UserOut, summary="Поменять роль(Для теста доступно всем ролям)")
def change_role(
    user_id: int,
    payload: UserRoleUpdate = Depends(UserRoleUpdate.as_form),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    if not settings.ALLOW_ROLE_SELF_ASSIGN:
        if current.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="Только для админа")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.role = payload.role
    db.add(user)
    db.flush()
    db.refresh(user)
    return user
