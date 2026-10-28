"""Allowlisted public directory fields. Never reuse private admin schemas here."""

import datetime

from pydantic import BaseModel, Field


class PublicEvent(BaseModel):
    Event_Name: str
    Event_Date: datetime.date
    Event_End_Date: datetime.date | None
    Location: str | None

    model_config = {"from_attributes": True}


class PublicPoster(BaseModel):
    Project_Number: str
    Project_Title: str
    Presenter_Display_Name: str
    Institution: str | None
    Table_Number: str | None
    Board_Label: str | None = None
    Poster_Session: str | None = None
    Poster_Session_Time: str | None = None


class PublicPosterDirectory(BaseModel):
    is_draft_preview: bool = False
    event: PublicEvent | None = None
    posters: list[PublicPoster] = Field(default_factory=list)
