"""Ballot rules, event isolation, code hashing, and replacement-safe entitlements."""

import base64
import datetime
import hashlib
import secrets
import time
from collections import OrderedDict, deque

from fastapi import HTTPException
from sqlalchemy import select, update

from app.config import settings
from app.models.ballot import Ballot
from app.models.ballot_selection import BallotSelection
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.project import Project
from app.models.talk import TalkBallot, TalkCandidate
from app.models.voting_round import VotingRound
from app.services.attendee_report import attendee_choice_report

UTC = datetime.timezone.utc
_attempts: OrderedDict[str, deque] = OrderedDict()


def utc(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def now():
    return datetime.datetime.now(UTC)


def code_hash(code: str) -> str:
    normalized = "".join(code.upper().split()).replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()


def issue_code() -> tuple[str, str]:
    code = base64.b32encode(secrets.token_bytes(10)).decode()
    return code, code_hash(code)


def check_login_rate(ip: str, digest: str, ip_limit=300, code_limit=8):
    moment = time.monotonic()
    for key, limit in (("ip:" + ip, ip_limit), ("code:" + digest, code_limit)):
        attempts = _attempts.setdefault(key, deque())
        while attempts and attempts[0] < moment - 600:
            attempts.popleft()
        if len(attempts) >= limit:
            raise HTTPException(
                429, "Too many voting-code attempts. Try again in ten minutes."
            )
        attempts.append(moment)
        _attempts.move_to_end(key)
    while len(_attempts) > 5000:
        _attempts.popitem(last=False)


async def lock_round(db, round_id):
    result = await db.execute(
        update(VotingRound)
        .where(VotingRound.Round_ID == round_id)
        .values(Status=VotingRound.Status)
    )
    if result.rowcount != 1:
        raise HTTPException(404, "Voting round not found")
    round_ = await db.get(VotingRound, round_id, populate_existing=True)
    return round_


async def eligible_posters(db, event_id):
    return list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id,
                Project.Category == "Poster",
                Project.Is_Active.is_(True),
                Project.Voting_Eligible.is_(True),
                Project.Roster_Review_Required.is_(False),
            )
        )
    )


async def round_candidates(db, round_):
    if round_.Candidate_Type == "talk":
        return list(
            await db.scalars(
                select(TalkCandidate).where(
                    TalkCandidate.Round_ID == round_.Round_ID,
                    TalkCandidate.Is_Active.is_(True),
                )
            )
        )
    return await eligible_posters(db, round_.Event_ID)


async def round_missing(db, round_) -> list[str]:
    missing = []
    event = await db.get(Event, round_.Event_ID)
    rules = await db.get(CompetitionSettings, round_.Event_ID)
    if not event.Is_Active and not (rules and rules.Is_Rehearsal and settings.dev_mode):
        missing.append("An active event (or synthetic dev rehearsal)")
    if round_.Public_Browser and (
        round_.Trainees_Only
        or round_.Allow_Self_Votes is not True
        or round_.Allow_Edits is not False
    ):
        missing.append("Open voting: all attendees, self-votes allowed, no edits")
    if not round_.Rules_Confirmed:
        missing.append("Organizer confirmation of voting rules")
    for field, label in (
        ("Min_Choices", "Minimum choices"),
        ("Max_Choices", "Maximum choices"),
        ("Ranked", "Ranked or unranked choices"),
        ("Allow_Self_Votes", "Self-voting policy"),
        ("Allow_Edits", "Ballot-edit policy"),
        ("Opens_At", "Opening time"),
        ("Closes_At", "Closing time"),
    ):
        if getattr(round_, field) is None:
            missing.append(label)
    if (
        round_.Opens_At
        and round_.Closes_At
        and utc(round_.Opens_At) >= utc(round_.Closes_At)
    ):
        missing.append("Closing time after opening time")
    if round_.Closes_At and utc(round_.Closes_At) <= now():
        missing.append("A future closing time")
    if (
        round_.Min_Choices
        and round_.Max_Choices
        and round_.Min_Choices > round_.Max_Choices
    ):
        missing.append("A valid ballot size range")
    active = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == round_.Event_ID,
                Project.Category == "Poster",
                Project.Is_Active.is_(True),
            )
        )
    )
    if round_.Candidate_Type == "talk":
        active = []
    pending = sum(p.Voting_Eligible is None for p in active)
    unresolved = sum(p.Roster_Review_Required for p in active)
    if pending:
        missing.append(f"Voting eligibility for {pending} presentations")
    if unresolved:
        missing.append(f"Roster decisions for {unresolved} active submissions")
    candidates = await round_candidates(db, round_)
    if not candidates:
        missing.append("Eligible posters")
    if round_.Min_Choices and round_.Min_Choices > len(candidates):
        missing.append("Enough eligible posters for the minimum choices")
    return missing


def voting_open(round_):
    return (
        round_.Status == "open"
        and round_.Rules_Confirmed
        and round_.Opens_At is not None
        and round_.Closes_At is not None
        and utc(round_.Opens_At) <= now() < utc(round_.Closes_At)
    )


async def ballot_read(db, round_id, voter_id):
    round_ = await db.get(VotingRound, round_id)
    if round_.Candidate_Type == "talk":
        ballot = await db.scalar(
            select(TalkBallot).where(
                TalkBallot.Round_ID == round_id, TalkBallot.Voter_ID == voter_id
            )
        )
        return {
            "saved": bool(ballot),
            "Project_IDs": ballot.Candidate_IDs if ballot else [],
            "Submitted_At": utc(ballot.Submitted_At) if ballot else None,
            "Updated_At": utc(ballot.Updated_At) if ballot else None,
        }
    ballot = await db.scalar(
        select(Ballot).where(Ballot.Round_ID == round_id, Ballot.Voter_ID == voter_id)
    )
    if not ballot:
        return {
            "saved": False,
            "Project_IDs": [],
            "Submitted_At": None,
            "Updated_At": None,
        }
    selections = list(
        await db.scalars(
            select(BallotSelection)
            .where(BallotSelection.Ballot_ID == ballot.Ballot_ID)
            .order_by(BallotSelection.Selection_ID)
        )
    )
    return {
        "saved": True,
        "Project_IDs": [s.Project_ID for s in selections],
        "Submitted_At": utc(ballot.Submitted_At),
        "Updated_At": utc(ballot.Updated_At),
    }


async def round_summary(db, round_):
    ballot_model = TalkBallot if round_.Candidate_Type == "talk" else Ballot
    ballots = list(
        await db.scalars(
            select(ballot_model).where(ballot_model.Round_ID == round_.Round_ID)
        )
    )
    # Counts and rank distributions are separate from a winner decision. No
    # unconfirmed weights are invented for ranked ballots.
    can_tally = round_.Status == "closed" or (
        round_.Closes_At and now() >= utc(round_.Closes_At) and round_.Status == "open"
    )
    tally = []
    if can_tally:
        eligible = {p.Project_ID: p for p in await round_candidates(db, round_)}
        selections = (
            await db.execute(
                select(BallotSelection.Project_ID, BallotSelection.Rank)
                .join(Ballot, Ballot.Ballot_ID == BallotSelection.Ballot_ID)
                .where(Ballot.Round_ID == round_.Round_ID)
            )
        ).all()
        if round_.Candidate_Type == "talk":
            selections = [
                (pid, index if round_.Ranked else None)
                for ballot in ballots
                for index, pid in enumerate(ballot.Candidate_IDs, 1)
            ]
        for project_id, project in eligible.items():
            ranks = [
                rank
                for pid, rank in selections
                if pid == project_id and rank is not None
            ]
            tally.append(
                {
                    "Project_Number": project.Project_Number,
                    "Presenter_Display_Name": project.Presenter_Display_Name
                    or (
                        f"{project.Presenter_First_Name} {project.Presenter_Last_Name}"
                    ).strip(),
                    "Project_Title": project.Project_Title,
                    "Votes": sum(pid == project_id for pid, _ in selections),
                    "Rank_Counts": {
                        str(rank): ranks.count(rank) for rank in sorted(set(ranks))
                    },
                }
            )
        tally.sort(key=lambda p: (-p["Votes"], p["Project_Number"]))
    return {
        "Round_ID": round_.Round_ID,
        "Round_Name": round_.Round_Name,
        "Ballots_Submitted": len(ballots),
        "Voting_Open": voting_open(round_),
        "Tallies_Available": bool(can_tally),
        "tally": tally,
        "Top_Ten_Report": attendee_choice_report(tally) if can_tally else None,
        "missing": await round_missing(db, round_) if round_.Status == "draft" else [],
    }
