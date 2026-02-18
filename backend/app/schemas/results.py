"""Results and aggregation schemas."""

from pydantic import BaseModel


class ProjectResult(BaseModel):
    """Aggregated scoring result for a single project."""

    Project_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Department: str | None
    Category: str
    Judge_Count: int
    Total_Score: int
    Average_Score: float
    Rank: int = 0


class EventSummary(BaseModel):
    """High-level event scoring statistics."""

    Total_Projects: int
    Total_Judges: int
    Total_Scores_Submitted: int
    Projects_With_Scores: int
    Scoring_Coverage_Percent: float
    Poster_Count: int
    Art_Count: int
