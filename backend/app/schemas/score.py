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


class ScoreOverrideUpdate(BaseModel):
    Score_Value: int


class ScoreOverrideRead(BaseModel):
    Override_ID: int
    Old_Score_Value: int
    New_Score_Value: int
    Admin_Username: str
    Overridden_At: datetime.datetime


class ProjectScoreReviewCriterion(BaseModel):
    Score_ID: int
    Criterion_ID: int
    Criterion_Name: str
    Criterion_Group: str | None
    Min_Score: int
    Max_Score: int
    Score_Value: int
    Original_Score_Value: int
    Override_Count: int
    Latest_Override: ScoreOverrideRead | None = None


class JudgeScoreReview(BaseModel):
    Judge_ID: str
    Judge_Name: str
    Judge_Department: str | None
    Submitted_At: datetime.datetime | None
    Total_Score: int
    Feedback_Text: str | None = None
    criteria: list[ProjectScoreReviewCriterion]


class ProjectScoreReview(BaseModel):
    Project_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Department: str | None
    Category: str
    submissions: list[JudgeScoreReview]
