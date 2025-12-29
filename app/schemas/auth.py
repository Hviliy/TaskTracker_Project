from fastapi import Form
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @classmethod
    def as_form(
            cls,
            name: str = Form(...),
            email: EmailStr = Form(...),
            password: str = Form(...),
    ) -> "UserCreate":
        return cls(name=name, email=email, password=password)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"