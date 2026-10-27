"""Nullable competition choices remain pending until an organizer confirms them."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CompetitionUpdate(BaseModel):
    Required_Reviews: int | None = Field(default=None, ge=1, le=100)
    Assignment_Only: bool | None = None
    Aggregation: Literal["average", "total"] | None = None
    Tie_Policy: Literal["shared", "manual"] | None = None
    Award_Groups: list[str] | None = Field(default=None, max_length=20)
    Rules_Confirmed: bool = False

    @field_validator("Award_Groups")
    @classmethod
    def clean_groups(cls, values):
        if values is None:
            return None
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 100 for value in cleaned) or len(
            set(cleaned)
        ) != len(cleaned):
            raise ValueError("Use distinct award group names of 1–100 characters")
        return cleaned


class CompetitionRead(CompetitionUpdate):
    Event_ID: str
    Judging_Open: bool = False
    model_config = {"from_attributes": True}


class ConflictCreate(BaseModel):
    Judge_ID: str
    Project_ID: str
    Reason: str = Field(min_length=1, max_length=500)


class AutoAssignmentCreate(BaseModel):
    Event_ID: str
    Judges_Per_Project: int | None = Field(default=None, ge=1, le=100)
    Category: Literal["Poster", "Art"] | None = None
