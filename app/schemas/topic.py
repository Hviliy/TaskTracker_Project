from fastapi import Form, HTTPException
from pydantic import BaseModel, Field, ValidationError, ConfigDict


class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @classmethod
    def as_form(
            cls,
            name: str = Form(...),
            description: str | None = Form(None),
    ) -> "TopicCreate":
        try:
            return cls(name=name, description=description)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

class TopicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @classmethod
    def as_form(
            cls,
            name: str | None = Form(None),
            description: str | None = Form(None),
    ) -> "TopicUpdate":
        try:
            return cls(name=name, description=description)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

class TopicOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)