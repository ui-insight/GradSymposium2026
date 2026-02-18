"""Event schemas."""

import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    Event_Name: str
    Event_Date: datetime.date
    Location: str | None = None
    Description: str | None = None
    Is_Active: bool = True


class EventUpdate(BaseModel):
    Event_Name: str | None = None
    Event_Date: datetime.date | None = None
    Location: str | None = None
    Description: str | None = None
    Is_Active: bool | None = None


class EventRead(BaseModel):
    Event_ID: str
    Event_Name: str
    Event_Date: datetime.date
    Location: str | None
    Description: str | None
    Is_Active: bool
    Created_At: datetime.datetime

    model_config = {"from_attributes": True}
