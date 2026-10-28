"""Judge schemas."""

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

JudgeName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class JudgeNameUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    First_Name: JudgeName
    Last_Name: JudgeName


class JudgeProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Judge_ID: str
    Event_ID: str
    First_Name: str
    Last_Name: str
    Name_Confirmed_At: datetime.datetime | None
    Conflict_Review_Required: bool


class JudgeCreate(BaseModel):
    Event_ID: str
    First_Name: JudgeName
    Last_Name: JudgeName
    Email: str | None = None
    Department: str | None = None


class JudgeUpdate(BaseModel):
    Is_Active: bool | None = None
    First_Name: JudgeName | None = None
    Last_Name: JudgeName | None = None
    Email: str | None = None
    Department: str | None = None
    Conflict_Review_Required: bool | None = None
    Reviewed_Name: str | None = Field(default=None, max_length=201)


class JudgeRead(BaseModel):
    Name_Confirmed_At: datetime.datetime | None = None
    Previous_Name: str | None = None
    Conflict_Review_Required: bool = False
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
