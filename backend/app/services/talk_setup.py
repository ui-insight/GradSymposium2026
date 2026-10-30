"""Repeatable draft preparation from Paul's supplied session lists."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from app.models.talk import TalkCandidate
from app.models.voting_round import VotingRound

SPEAKERS = {
    "Trainee talks people's choice": [
        ("Marisa Yonemitsu", "University of Washington"),
        ("Anastasia Chepel", "Washington State University"),
        ("Geraline Trossi-Torres", "University of Idaho"),
        ("Cameron Coyle", "Washington State University"),
        ("Sam Butler", "Boise State University"),
        ("Andrea Gómez", "Washington State University"),
        ("Gary Dunn", "University of Idaho"),
        ("Anita Paneru", "Washington State University"),
    ],
    "Main-session short talks people's choice": [
        ("Sarina Kao", "University of Washington"),
        ("Shun-Je Bhark", "Oregon Health & Science University"),
        ("Victoria Jefferson", "Washington State University"),
        ("Jyoti Kashyap", "University of Idaho"),
        ("Peyton Fox", None),
        ("L. America Chi", "University of Idaho"),
    ],
}


async def prepare_talks(db, event_id):
    for name, speakers in SPEAKERS.items():
        rounds = list(
            await db.scalars(
                select(VotingRound).where(
                    VotingRound.Event_ID == event_id, VotingRound.Round_Name == name
                )
            )
        )
        if rounds:
            raise HTTPException(
                409,
                "Named talk rounds already exist. Review them; "
                "preparation will not overwrite organizer changes.",
            )
    for index, (name, speakers) in enumerate(SPEAKERS.items()):
        zone = ZoneInfo("America/Los_Angeles")
        opens = (
            datetime(2026, 10, 31, 12, 20, tzinfo=zone)
            if index == 0
            else datetime(2026, 11, 1, 9, 10, tzinfo=zone)
        )
        closes = (
            datetime(2026, 10, 31, 15, 45, tzinfo=zone)
            if index == 0
            else datetime(2026, 11, 1, 17, 0, tzinfo=zone)
        )
        round_ = VotingRound(
            Event_ID=event_id,
            Round_Name=name,
            Candidate_Type="talk",
            Trainees_Only=True,
            Min_Choices=1,
            Max_Choices=1,
            Ranked=False,
            Allow_Self_Votes=False,
            Allow_Edits=False,
            Opens_At=opens,
            Closes_At=closes,
        )
        db.add(round_)
        await db.flush()
        for speaker, institution in speakers:
            db.add(
                TalkCandidate(
                    Round_ID=round_.Round_ID,
                    Presenter_Display_Name=speaker,
                    Institution=institution,
                )
            )
    await db.commit()
