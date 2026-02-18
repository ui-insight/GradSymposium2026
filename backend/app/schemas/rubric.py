"""Rubric and criterion schemas."""

from pydantic import BaseModel


class CriterionCreate(BaseModel):
    Criterion_Name: str
    Criterion_Group: str | None = None
    Description: str | None = None
    Min_Score: int = 0
    Max_Score: int = 3
    Sort_Order: int = 0


class CriterionUpdate(BaseModel):
    Criterion_Name: str | None = None
    Criterion_Group: str | None = None
    Description: str | None = None
    Min_Score: int | None = None
    Max_Score: int | None = None
    Sort_Order: int | None = None


class CriterionRead(BaseModel):
    Criterion_ID: int
    Rubric_ID: str
    Criterion_Name: str
    Criterion_Group: str | None
    Description: str | None
    Min_Score: int
    Max_Score: int
    Sort_Order: int

    model_config = {"from_attributes": True}


class RubricRead(BaseModel):
    Rubric_ID: str
    Event_ID: str
    Rubric_Name: str
    Category: str
    Max_Score: int
    Description: str | None
    criteria: list[CriterionRead] = []

    model_config = {"from_attributes": True}


class RubricUpdate(BaseModel):
    Rubric_Name: str | None = None
    Description: str | None = None
