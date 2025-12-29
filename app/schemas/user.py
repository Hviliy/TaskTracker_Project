from fastapi import Form, HTTPException
from pydantic import BaseModel, ValidationError, ConfigDict
from app.db.models import UserRole

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class UserRoleUpdate(BaseModel):
    role: UserRole

    @classmethod
    def as_form(cls, role: UserRole = Form(...)) -> "UserRoleUpdate":
        try:
            return cls(role=role)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
