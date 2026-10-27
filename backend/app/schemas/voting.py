"""Separate voter credentials and explicit, organizer-confirmed ballot rules."""

import datetime

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class VotingRoundUpdate(BaseModel):
    Round_Name: str = Field(min_length=1, max_length=200)
    Min_Choices: int | None = Field(default=None, ge=1, le=100)
    Max_Choices: int | None = Field(default=None, ge=1, le=100)
    Ranked: bool | None = None
    Allow_Self_Votes: bool | None = None
    Allow_Edits: bool | None = None
    Opens_At: datetime.datetime | None = None
    Closes_At: datetime.datetime | None = None
    Rules_Confirmed: bool = False

    @field_validator("Opens_At", "Closes_At")
    @classmethod
    def aware_time(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Include a timezone offset for voting times")
        return value.astimezone(datetime.timezone.utc) if value else None

    @model_validator(mode="after")
    def coherent_rules(self):
        if (
            self.Min_Choices
            and self.Max_Choices
            and self.Min_Choices > self.Max_Choices
        ):
            raise ValueError("Minimum choices cannot exceed maximum choices")
        if self.Opens_At and self.Closes_At and self.Opens_At >= self.Closes_At:
            raise ValueError("Closing time must follow opening time")
        return self


class VotingRoundCreate(VotingRoundUpdate):
    Event_ID: str


class VotingRoundRead(BaseModel):
    Round_ID: str
    Event_ID: str
    Round_Name: str
    Status: str
    Min_Choices: int | None
    Max_Choices: int | None
    Ranked: bool | None
    Allow_Self_Votes: bool | None
    Allow_Edits: bool | None
    Opens_At: datetime.datetime | None
    Closes_At: datetime.datetime | None
    Rules_Confirmed: bool
    model_config = {"from_attributes": True}

    @field_serializer("Opens_At", "Closes_At")
    def serialize_time(self, value):
        if value is not None:
            return (
                value.replace(tzinfo=datetime.timezone.utc)
                if value.tzinfo is None
                else value
            )
        return None


class VoterCreate(BaseModel):
    Event_ID: str
    Registration_Reference: str = Field(min_length=1, max_length=200)
    Affiliation_Confirmed: bool = False
    Presenter_Project_IDs: list[str] = Field(default_factory=list, max_length=100)


class VoterUpdate(BaseModel):
    Affiliation_Confirmed: bool
    Presenter_Project_IDs: list[str] = Field(max_length=100)


class VoterBulkCreate(BaseModel):
    Event_ID: str
    Registration_References: list[str] = Field(min_length=1, max_length=500)


class VoterRead(BaseModel):
    Voter_ID: str
    Event_ID: str
    Registration_Reference: str
    Is_Active: bool
    Affiliation_Confirmed: bool
    Presenter_Project_IDs: list[str]
    model_config = {"from_attributes": True}


class VoterLogin(BaseModel):
    access_code: str = Field(min_length=1, max_length=100)


class BallotCreate(BaseModel):
    Project_IDs: list[str] = Field(min_length=1, max_length=100)
