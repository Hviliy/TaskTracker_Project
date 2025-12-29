from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.db.models import User
from app.schemas.auth import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["Авторизация"])

@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Регистрация")
def register(payload: UserCreate = Depends(UserCreate.as_form), db: Session = Depends(get_db)) -> dict:
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Почта уже зарегистрирована")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/login", response_model=Token, summary="Логин")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)