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


class PublicPosterDirectory(BaseModel):
    event: PublicEvent | None = None
    posters: list[PublicPoster] = Field(default_factory=list)
