from fastapi import Form, HTTPException
from pydantic import BaseModel, Field, ValidationError


class TaskStatusChange(BaseModel):
    status_code: str = Field(min_length=1, max_length=50)

    @classmethod
    def as_form(cls, status_code: str = Form(...)) -> 'TaskStatusChange':
        try:
            return cls(status_code=status_code)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.detail)