"""Judge schemas."""

from pydantic import BaseModel, Field, field_validator


class JudgeCreate(BaseModel):
    Event_ID: str
    First_Name: str = Field(min_length=1, max_length=100)
    Last_Name: str = Field(min_length=1, max_length=100)
    Email: str | None = None
    Department: str | None = None

    @field_validator("First_Name", "Last_Name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("Provide a name")
        return value.strip()


class JudgeUpdate(BaseModel):
    Is_Active: bool | None = None
    First_Name: str | None = None
    Last_Name: str | None = None
    Email: str | None = None
    Department: str | None = None


class JudgeRead(BaseModel):
    Judge_ID: str
    Event_ID: str
    First_Name: str
    Last_Name: str
    Email: str | None
    Department: str | None
    Access_Code: str
    Is_Active: bool
    assignment_count: int = 0
    score_count: int = 0

    model_config = {"from_attributes": True}


class JudgeBulkCreate(BaseModel):
    Event_ID: str
    judges: list[JudgeCreate]


class AccessCodeCard(BaseModel):
    First_Name: str
    Last_Name: str
    Access_Code: str
