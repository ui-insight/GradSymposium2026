"""Project schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    Event_ID: str
    Project_Number: str | None = Field(default=None, max_length=20)
    Project_Title: str = Field(min_length=1, max_length=500)
    Presenter_First_Name: str = Field(default="", max_length=100)
    Presenter_Last_Name: str = Field(default="", max_length=100)
    Presenter_Display_Name: str | None = Field(default=None, max_length=300)
    Institution: str | None = Field(default=None, max_length=200)
    Judging_Eligible: bool | None = None
    Voting_Eligible: bool | None = None
    Award_Groups: list[str] | None = Field(default=None, max_length=20)
    Presenter_Email: str | None = Field(default=None, max_length=200)
    Department: str | None = Field(default=None, max_length=200)
    College: str | None = Field(default=None, max_length=200)
    Advisor_Name: str | None = Field(default=None, max_length=200)
    Category: Literal["Poster", "Art"]
    Table_Number: str | None = Field(default=None, max_length=20)

    @field_validator("Award_Groups")
    @classmethod
    def clean_groups(cls, groups):
        if groups is None:
            return None
        values = [value.strip() for value in groups]
        if any(not value or len(value) > 100 for value in values) or len(values) != len(
            set(values)
        ):
            raise ValueError("Use distinct award group names of 1–100 characters")
        return values

    @model_validator(mode="after")
    def require_presenter(self):
        if not (self.Presenter_Display_Name or "").strip() and not (
            self.Presenter_First_Name.strip() and self.Presenter_Last_Name.strip()
        ):
            raise ValueError("Provide a display name or both first and last names")
        if not self.Project_Title.strip():
            raise ValueError("Title must not be blank")
        return self


class ProjectUpdate(BaseModel):
    Judging_Eligible: bool | None = None
    Voting_Eligible: bool | None = None
    Award_Groups: list[str] | None = Field(default=None, max_length=20)
    Project_Number: str | None = None
    Project_Title: str | None = None
    Presenter_First_Name: str | None = None
    Presenter_Last_Name: str | None = None
    Presenter_Email: str | None = None
    Presenter_Display_Name: str | None = Field(default=None, max_length=300)
    Institution: str | None = Field(default=None, max_length=200)
    Department: str | None = None
    College: str | None = None
    Advisor_Name: str | None = None
    Category: Literal["Poster", "Art"] | None = None
    Table_Number: str | None = None


class ProjectRead(BaseModel):
    Judging_Eligible: bool | None = None
    Voting_Eligible: bool | None = None
    Award_Groups: list[str] | None = None
    Project_ID: str
    Event_ID: str
    Project_Number: str
    Project_Title: str
    Presenter_First_Name: str
    Presenter_Last_Name: str
    Presenter_Email: str | None
    Presenter_Display_Name: str | None
    Institution: str | None
    Is_Published: bool
    Roster_Review: dict | None
    Roster_Review_Required: bool
    Department: str | None
    College: str | None
    Advisor_Name: str | None
    Category: str
    Table_Number: str | None
    Is_Active: bool
    score_count: int = 0

    model_config = {"from_attributes": True}


class PosterPublication(BaseModel):
    Event_ID: str
    Is_Published: bool


class CSVImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    preview: list[ProjectRead] = Field(default_factory=list)
