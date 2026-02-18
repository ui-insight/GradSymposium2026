"""Project schemas."""

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    Event_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Presenter_Email: str | None = None
    Department: str | None = None
    College: str | None = None
    Advisor_Name: str | None = None
    Category: str  # "Poster" or "Art"
    Table_Number: str | None = None


class ProjectUpdate(BaseModel):
    Project_Number: str | None = None
    Project_Title: str | None = None
    Presenter_First_Name: str | None = None
    Presenter_Last_Name: str | None = None
    Presenter_Email: str | None = None
    Department: str | None = None
    College: str | None = None
    Advisor_Name: str | None = None
    Category: str | None = None
    Table_Number: str | None = None


class ProjectRead(BaseModel):
    Project_ID: str
    Event_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Presenter_Email: str | None
    Department: str | None
    College: str | None
    Advisor_Name: str | None
    Category: str
    Table_Number: str | None
    Is_Active: bool
    score_count: int = 0

    model_config = {"from_attributes": True}


class CSVImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
