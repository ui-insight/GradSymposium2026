"""Organizer-supplied session labels, never inferred from a schedule."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionProposal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    Odd_Session: Literal["I", "II"]
    Session_I_Time: str = Field(min_length=1, max_length=150)
    Session_II_Time: str = Field(min_length=1, max_length=150)


class SessionApply(SessionProposal):
    Context: str
    Reference: str = Field(min_length=1, max_length=500)
    Organizer_Confirmed: Literal[True]
    Unassigned_Numbers_Confirmed: bool = False
