"""Rubric and criterion schemas."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CriterionCreate(BaseModel):
    Criterion_Name: str = Field(min_length=1, max_length=200)
    Criterion_Group: str | None = None
    Description: str | None = None
    Min_Score: int = Field(default=0, ge=0, le=3)
    Max_Score: int = Field(default=3, ge=0, le=3)
    Sort_Order: int = 0

    @model_validator(mode="after")
    def valid_range(self):
        if not self.Criterion_Name.strip() or self.Min_Score >= self.Max_Score:
            raise ValueError(
                "Provide a criterion name and a maximum greater than minimum "
                "(supported range 0–3)"
            )
        return self


class RubricCreate(BaseModel):
    Event_ID: str
    Rubric_Name: str = Field(min_length=1, max_length=100)
    Category: Literal["Poster", "Art"]
    Description: str | None = None


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
    Is_Locked: bool = False
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
