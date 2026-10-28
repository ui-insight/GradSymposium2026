"""Results and aggregation schemas."""

from pydantic import BaseModel, Field


class ProjectResult(BaseModel):
    """Aggregated scoring result for a single project."""

    Project_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Presenter_Display_Name: str | None = None
    Department: str | None
    Category: str
    Judge_Count: int
    Total_Score: int
    Average_Score: float
    Rank: int = 0
    Required_Reviews: int | None = None
    Meets_Review_Target: bool | None = None
    Award_Groups: list[str] = Field(default_factory=list)
    Tied: bool = False
    Provisional: bool = False


class EventSummary(BaseModel):
    """High-level event scoring statistics."""

    Total_Projects: int
    Total_Judges: int
    Total_Scores_Submitted: int
    Projects_With_Scores: int
    Scoring_Coverage_Percent: float
    Poster_Count: int
    Art_Count: int
    Eligible_Projects: int = 0
    Required_Reviews: int | None = None
    Projects_At_Target: int = 0
    Judging_Open: bool = False
