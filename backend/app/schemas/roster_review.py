"""Organizer intent and stale-view tokens for the final roster workspace."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Reason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Context = Annotated[str, StringConstraints(min_length=64, max_length=64)]


class RosterTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Project_ID: str
    Context: Context


class RosterAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Action: Literal["accept", "withdraw", "reopen"]
    Reason: Reason
    Targets: list[RosterTarget] = Field(min_length=1, max_length=500)
    Distinct_Verified: bool = False
    Talk_Only_Confirmed: bool = False
    Superseded_By: str | None = None


class DuplicateResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Keep: RosterTarget
    Withdraw: RosterTarget
    Reason: Reason
    Source_Verified: Literal[True]
    Talk_Only_Confirmed: bool = False


class RosterCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Context: Context
    Reason: Reason
    Project_Title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    Presenter_Display_Name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
    ]
    Institution: str | None = Field(default=None, max_length=200)
    Advisor_Name: str | None = Field(default=None, max_length=200)
    Table_Number: str | None = Field(default=None, max_length=20)


class FinalRosterSignoff(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Context: Context
    Accepted_Count: int = Field(ge=1)
    Source_Count: int = Field(ge=0)
    Reference: Reason
    Final_Changes_Confirmed: Literal[True]
    Preview_Reviewed: Literal[True]
