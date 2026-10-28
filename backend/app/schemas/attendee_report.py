"""Allowlisted closed-round attendee-choice report, separate from rubric scores."""

from pydantic import BaseModel


class AttendeeChoiceEntry(BaseModel):
    Project_Number: str
    Presenter_Display_Name: str
    Project_Title: str
    Votes: int
    Vote_Rank: int
    Tied_Count: int


class AttendeeChoiceReport(BaseModel):
    Eligible_Count: int
    Top_Ten: list[AttendeeChoiceEntry]
    Additional_Cutoff_Ties: list[AttendeeChoiceEntry]
    Cutoff_Votes: int | None
    Cutoff_Spans_Ten: bool
