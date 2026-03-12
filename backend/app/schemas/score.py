"""Score schemas."""

import datetime

from pydantic import BaseModel


class ScoreEntry(BaseModel):
    """A single criterion score within a submission."""

    Criterion_ID: int
    Score_Value: int  # 0-3


class ScoreSubmission(BaseModel):
    """All criterion scores for a project, submitted by a judge."""

    scores: list[ScoreEntry]
    feedback: str | None = None


class ScoreRead(BaseModel):
    Score_ID: int
    Judge_ID: str
    Project_ID: str
    Criterion_ID: int
    Score_Value: int
    Scored_At: datetime.datetime

    model_config = {"from_attributes": True}
