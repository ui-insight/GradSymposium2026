"""Judge schemas."""

from pydantic import BaseModel


class JudgeCreate(BaseModel):
    Event_ID: str
    First_Name: str
    Last_Name: str
    Email: str | None = None
    Department: str | None = None


class JudgeUpdate(BaseModel):
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
    score_count: int = 0

    model_config = {"from_attributes": True}


class JudgeBulkCreate(BaseModel):
    Event_ID: str
    judges: list[JudgeCreate]


class AccessCodeCard(BaseModel):
    First_Name: str
    Last_Name: str
    Access_Code: str
