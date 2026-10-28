"""Explicit organizer decisions; never infer a clear relationship from a search."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class MentorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Context: str = Field(min_length=64, max_length=64)
    Decision: Literal["clear", "conflict", "needs_input"]
    Note: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]


class MentorCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Context: str = Field(min_length=64, max_length=64)
