"""Rubric and criterion schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class RubricScale(BaseModel):
    Score_Labels: dict[int, str] | None = None

    @field_validator("Score_Labels")
    @classmethod
    def valid_labels(cls, labels):
        if labels is not None and any(
            key < 0 or key > 5 or not label.strip() or len(label) > 100
            for key, label in labels.items()
        ):
            raise ValueError("Use score keys 0–5 and labels of 1–100 characters")
        return labels


class CriterionCreate(BaseModel):
    Criterion_Name: str = Field(min_length=1, max_length=200)
    Criterion_Group: str | None = None
    Description: str | None = None
    Min_Score: int = Field(default=0, strict=True, ge=0, le=5)
    Max_Score: int = Field(default=3, strict=True, ge=0, le=5)
    Sort_Order: int = 0

    @model_validator(mode="after")
    def valid_range(self):
        if not self.Criterion_Name.strip() or self.Min_Score >= self.Max_Score:
            raise ValueError(
                "Provide a criterion name and a maximum greater than minimum "
                "(supported range 0–5)"
            )
        return self


class RubricCreate(RubricScale):
    Event_ID: str
    Rubric_Name: str = Field(min_length=1, max_length=100)
    Category: Literal["Poster", "Art"]
    Description: str | None = None


class CriterionUpdate(BaseModel):
    Criterion_Name: str | None = None
    Criterion_Group: str | None = None
    Description: str | None = None
    Min_Score: int | None = Field(default=None, strict=True, ge=0, le=5)
    Max_Score: int | None = Field(default=None, strict=True, ge=0, le=5)
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


class RubricRead(RubricScale):
    Is_Locked: bool = False
    Rubric_ID: str
    Event_ID: str
    Rubric_Name: str
    Category: str
    Max_Score: int
    Description: str | None
    criteria: list[CriterionRead] = []

    model_config = {"from_attributes": True}


class RubricUpdate(RubricScale):
    Rubric_Name: str | None = None
    Description: str | None = None
