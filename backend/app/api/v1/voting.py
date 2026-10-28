"""Separate voter login/ballots and organizer management of voting entitlements."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, oauth2_scheme
from app.auth.jwt import create_access_token, decode_token
from app.config import settings
from app.models.ballot import Ballot
from app.models.ballot_selection import BallotSelection
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.project import Project
from app.models.user import User
from app.models.voter import Voter
from app.models.voting_round import VotingRound
from app.schemas.voting import (
    BallotCreate,
    VoterBulkCreate,
    VoterCreate,
    VoterLogin,
    VoterRead,
    VoterUpdate,
    VotingRoundCreate,
    VotingRoundRead,
    VotingRoundUpdate,
)
from app.services.competition import lock_event
from app.services.voting import (
    ballot_read,
    check_login_rate,
    code_hash,
    eligible_posters,
    issue_code,
    lock_round,
    now,
    round_missing,
    round_summary,
    voting_open,
)

router = APIRouter(prefix="/voting", tags=["attendee voting"])


async def current_voter(
    token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    payload = decode_token(token) if token else None
    if not payload or payload.get("role") != "voter":
        raise HTTPException(401, "Enter your voting code")
    voter = await db.get(Voter, payload.get("sub", ""))
    if (
        not voter
        or not voter.Is_Active
        or payload.get("credential_version") != voter.Credential_Version
    ):
        raise HTTPException(401, "This voting code has expired or been replaced")
    return voter


async def _round_for_voter(db, round_id, voter):
    round_ = await db.get(VotingRound, round_id)
    if not round_ or round_.Event_ID != voter.Event_ID:
        raise HTTPException(404, "Voting round not found for this code")
    return round_


async def _validate_links(db, event_id, identifiers):
    if len(identifiers) != len(set(identifiers)):
        raise HTTPException(422, "Duplicate poster affiliations")
    ids = (
        set(
            await db.scalars(
                select(Project.Project_ID).where(
                    Project.Event_ID == event_id, Project.Project_ID.in_(identifiers)
                )
            )
        )
        if identifiers
        else set()
    )
    if ids != set(identifiers):
        raise HTTPException(422, "Poster affiliations must belong to this event")


@router.post("/login")
async def login(body: VoterLogin, request: Request, db: AsyncSession = Depends(get_db)):
    digest = code_hash(body.access_code)
    check_login_rate(request.client.host if request.client else "unknown", digest)
    voter = await db.scalar(
        select(Voter).where(Voter.Code_Hash == digest, Voter.Is_Active.is_(True))
    )
    if not voter:
        raise HTTPException(401, "Invalid or inactive voting code")
    return {
        "access_token": create_access_token(
            voter.Voter_ID,
            "voter",
            extra_claims={"credential_version": voter.Credential_Version},
        ),
        "token_type": "bearer",
    }


@router.get("/rounds", response_model=list[VotingRoundRead])
async def public_rounds(db: AsyncSession = Depends(get_db)):
    active = list(
        await db.scalars(select(Event.Event_ID).where(Event.Is_Active.is_(True)))
    )
    if len(active) != 1:
        return []
    return list(
        await db.scalars(
            select(VotingRound)
            .where(VotingRound.Event_ID == active[0])
            .order_by(VotingRound.Round_Name)
        )
    )


@router.get("/me")
async def me(voter: Voter = Depends(current_voter), db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, voter.Event_ID)
    rules = await db.get(CompetitionSettings, voter.Event_ID)
    rounds = list(
        await db.scalars(
            select(VotingRound)
            .where(VotingRound.Event_ID == voter.Event_ID)
            .order_by(VotingRound.Round_Name)
        )
    )
    return {
        "Event_Name": event.Event_Name,
        "Is_Rehearsal": bool(rules and rules.Is_Rehearsal),
        "Affiliation_Confirmed": voter.Affiliation_Confirmed,
        "Presenter_Project_IDs": voter.Presenter_Project_IDs,
        "rounds": [
            VotingRoundRead.model_validate(r).model_dump(mode="json") for r in rounds
        ],
    }


@router.get("/rounds/{round_id}/posters")
async def posters(
    round_id: str,
    voter: Voter = Depends(current_voter),
    db: AsyncSession = Depends(get_db),
):
    round_ = await _round_for_voter(db, round_id, voter)
    candidates = await eligible_posters(db, voter.Event_ID)
    return [
        {
            "Project_ID": p.Project_ID,
            "Project_Number": p.Project_Number,
            "Project_Title": p.Project_Title,
            "Presenter_Display_Name": p.Presenter_Display_Name
            or f"{p.Presenter_First_Name} {p.Presenter_Last_Name}".strip(),
            "Institution": p.Institution,
            "Can_Select": round_.Allow_Self_Votes is True
            or p.Project_ID not in voter.Presenter_Project_IDs,
        }
        for p in sorted(candidates, key=lambda p: p.Project_Number)
    ]


@router.get("/rounds/{round_id}/ballot")
async def get_ballot(
    round_id: str,
    voter: Voter = Depends(current_voter),
    db: AsyncSession = Depends(get_db),
):
    await _round_for_voter(db, round_id, voter)
    return await ballot_read(db, round_id, voter.Voter_ID)


@router.post("/rounds/{round_id}/ballot")
async def submit_ballot(
    round_id: str,
    body: BallotCreate,
    voter: Voter = Depends(current_voter),
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    await lock_event(db, voter.Event_ID)
    round_ = await lock_round(db, round_id)
    if round_.Event_ID != voter.Event_ID:
        raise HTTPException(404, "Voting round not found for this code")
    # Refresh the entitlement after taking the round lock, so revocation and
    # credential replacement cannot leave an indefinitely usable session.
    await db.refresh(voter)
    payload = decode_token(token) if token else None
    if (
        not voter.Is_Active
        or not payload
        or payload.get("credential_version") != voter.Credential_Version
    ):
        raise HTTPException(401, "This voting code is inactive")
    event = await db.get(Event, voter.Event_ID)
    rules = await db.get(CompetitionSettings, voter.Event_ID)
    if not event.Is_Active and not (rules and rules.Is_Rehearsal and settings.dev_mode):
        raise HTTPException(409, "This event is archived; voting is closed")
    if not voting_open(round_):
        raise HTTPException(409, "Voting is not open for this round")
    ids = body.Project_IDs
    if not round_.Min_Choices <= len(ids) <= round_.Max_Choices or len(ids) != len(
        set(ids)
    ):
        raise HTTPException(
            422, "Choose distinct posters within this round's ballot size limits"
        )
    candidates = {p.Project_ID for p in await eligible_posters(db, voter.Event_ID)}
    if not set(ids) <= candidates:
        raise HTTPException(
            422, "A selected poster is withdrawn or not eligible in this round"
        )
    if round_.Allow_Self_Votes is not True:
        if not voter.Affiliation_Confirmed:
            raise HTTPException(
                409,
                "Registration staff must confirm your poster affiliation "
                "before you vote",
            )
        if set(ids) & set(voter.Presenter_Project_IDs):
            raise HTTPException(
                422, "This round does not allow voting for your own poster"
            )
    ballot = await db.scalar(
        select(Ballot).where(
            Ballot.Round_ID == round_id, Ballot.Voter_ID == voter.Voter_ID
        )
    )
    if ballot:
        previous = await ballot_read(db, round_id, voter.Voter_ID)
        same = (
            previous["Project_IDs"] == ids
            if round_.Ranked
            else set(previous["Project_IDs"]) == set(ids)
        )
        if same:
            await db.rollback()
            return previous
        if not round_.Allow_Edits:
            raise HTTPException(
                409, "Your ballot is already saved; this round does not allow changes"
            )
        await db.execute(
            delete(BallotSelection).where(BallotSelection.Ballot_ID == ballot.Ballot_ID)
        )
        ballot.Updated_At = now()
    else:
        ballot = Ballot(Round_ID=round_id, Voter_ID=voter.Voter_ID)
        db.add(ballot)
        await db.flush()
    for index, project_id in enumerate(ids, start=1):
        db.add(
            BallotSelection(
                Ballot_ID=ballot.Ballot_ID,
                Project_ID=project_id,
                Rank=index if round_.Ranked else None,
            )
        )
    await db.commit()
    return await ballot_read(db, round_id, voter.Voter_ID)


@router.get("/admin/rounds", response_model=list[VotingRoundRead])
async def admin_rounds(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return list(
        await db.scalars(
            select(VotingRound)
            .where(VotingRound.Event_ID == event_id)
            .order_by(VotingRound.Round_Name)
        )
    )


@router.post("/admin/rounds", response_model=VotingRoundRead, status_code=201)
async def create_round(
    body: VotingRoundCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, body.Event_ID)
    round_ = VotingRound(**body.model_dump())
    db.add(round_)
    await db.commit()
    await db.refresh(round_)
    return round_


@router.put("/admin/rounds/{round_id}", response_model=VotingRoundRead)
async def update_round(
    round_id: str,
    body: VotingRoundUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    round_ = await lock_round(db, round_id)
    count = await db.scalar(
        select(func.count()).select_from(Ballot).where(Ballot.Round_ID == round_id)
    )
    if round_.Status != "draft" or count:
        raise HTTPException(409, "Round rules are frozen once voting is opened")
    for key, value in body.model_dump().items():
        setattr(round_, key, value)
    await db.commit()
    await db.refresh(round_)
    return round_


@router.post("/admin/rounds/{round_id}/open", response_model=VotingRoundRead)
async def open_round(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    existing = await db.get(VotingRound, round_id)
    if not existing:
        raise HTTPException(404, "Round not found")
    await lock_event(db, existing.Event_ID)
    round_ = await lock_round(db, round_id)
    if round_.Status != "draft":
        raise HTTPException(409, "Only a draft round can be opened")
    missing = await round_missing(db, round_)
    if missing:
        raise HTTPException(409, "Voting is not ready: " + "; ".join(missing))
    round_.Status = "open"
    await db.commit()
    await db.refresh(round_)
    return round_


@router.post("/admin/rounds/{round_id}/close", response_model=VotingRoundRead)
async def close_round(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    round_ = await lock_round(db, round_id)
    if round_.Status == "draft":
        raise HTTPException(409, "This round has not been opened")
    round_.Status = "closed"
    await db.commit()
    await db.refresh(round_)
    return round_


@router.get("/admin/rounds/{round_id}/summary")
async def summary(
    round_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    round_ = await db.get(VotingRound, round_id)
    if not round_:
        raise HTTPException(404, "Round not found")
    response.headers["Cache-Control"] = "no-store"
    return await round_summary(db, round_)


@router.get("/admin/rounds/{round_id}/export")
async def export(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    round_ = await db.get(VotingRound, round_id)
    if not round_:
        raise HTTPException(404, "Round not found")
    state = await round_summary(db, round_)
    if not state["Tallies_Available"]:
        raise HTTPException(409, "Vote totals stay private until voting closes")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Poster", "Presenter", "Title", "Votes", "Rank counts (no weighting applied)"]
    )
    for item in state["tally"]:
        # Spreadsheet-safe text, including user-supplied names and titles.
        def safe(value):
            return (
                "'" + value
                if str(value).lstrip().startswith(("=", "+", "-", "@"))
                else value
            )

        writer.writerow(
            [
                safe(item["Project_Number"]),
                safe(item["Presenter_Display_Name"]),
                safe(item["Project_Title"]),
                item["Votes"],
                str(item["Rank_Counts"]),
            ]
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendee-votes.csv"'},
    )


@router.get("/admin/rounds/{round_id}/top-ten/export")
async def export_top_ten(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    round_ = await db.get(VotingRound, round_id)
    if not round_:
        raise HTTPException(404, "Round not found")
    state = await round_summary(db, round_)
    if not state["Tallies_Available"]:
        raise HTTPException(409, "Vote totals stay private until voting closes")
    report = state["Top_Ten_Report"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Round",
            "Report section",
            "Vote rank",
            "Tied posters",
            "Poster",
            "Presenter",
            "Title",
            "Votes",
            "Cutoff tie",
            "Ordering note",
        ]
    )

    def safe(value):
        text = str(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    for section, rows in (
        ("Top ten", report["Top_Ten"]),
        ("Additional cutoff tie", report["Additional_Cutoff_Ties"]),
    ):
        for row in rows:
            writer.writerow(
                [
                    safe(round_.Round_Name),
                    section,
                    row["Vote_Rank"],
                    row["Tied_Count"],
                    safe(row["Project_Number"]),
                    safe(row["Presenter_Display_Name"]),
                    safe(row["Project_Title"]),
                    row["Votes"],
                    "Yes"
                    if report["Cutoff_Spans_Ten"]
                    and row["Votes"] == report["Cutoff_Votes"]
                    else "No",
                    "Unweighted vote counts; equal counts share rank. "
                    "Poster-number ordering does not break ties or select winners.",
                ]
            )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="attendee-choice-top-ten.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/admin/voters", response_model=list[VoterRead])
async def voters(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return list(
        await db.scalars(
            select(Voter)
            .where(Voter.Event_ID == event_id)
            .order_by(Voter.Registration_Reference)
        )
    )


@router.post("/admin/voters", status_code=201)
async def create_voter(
    body: VoterCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, body.Event_ID)
    reference = body.Registration_Reference.strip().casefold()
    if not reference:
        raise HTTPException(422, "Provide a unique registration reference")
    if await db.scalar(
        select(Voter.Voter_ID).where(
            Voter.Event_ID == body.Event_ID, Voter.Registration_Reference == reference
        )
    ):
        raise HTTPException(
            409,
            "This registration already has an entitlement; replace its code instead",
        )
    await _validate_links(db, body.Event_ID, body.Presenter_Project_IDs)
    code, digest = issue_code()
    voter = Voter(
        Event_ID=body.Event_ID,
        Registration_Reference=reference,
        Code_Hash=digest,
        Affiliation_Confirmed=body.Affiliation_Confirmed,
        Presenter_Project_IDs=body.Presenter_Project_IDs,
    )
    db.add(voter)
    await db.commit()
    await db.refresh(voter)
    return {"voter": VoterRead.model_validate(voter), "access_code": code}


@router.post("/admin/voters/bulk", status_code=201)
async def bulk_voters(
    body: VoterBulkCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, body.Event_ID)
    references = [value.strip().casefold() for value in body.Registration_References]
    if any(not value or len(value) > 200 for value in references) or len(
        set(references)
    ) != len(references):
        raise HTTPException(
            422, "Use distinct registration references of 1–200 characters"
        )
    if await db.scalar(
        select(Voter.Voter_ID).where(
            Voter.Event_ID == body.Event_ID,
            Voter.Registration_Reference.in_(references),
        )
    ):
        raise HTTPException(
            409,
            "One or more registrations already have codes; replace those codes instead",
        )
    issued = []
    for reference in references:
        code, digest = issue_code()
        voter = Voter(
            Event_ID=body.Event_ID,
            Registration_Reference=reference,
            Code_Hash=digest,
            Affiliation_Confirmed=False,
            Presenter_Project_IDs=[],
        )
        db.add(voter)
        await db.flush()
        issued.append({"voter": VoterRead.model_validate(voter), "access_code": code})
    await db.commit()
    return issued


@router.put("/admin/voters/{voter_id}", response_model=VoterRead)
async def update_voter(
    voter_id: str,
    body: VoterUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    voter = await db.get(Voter, voter_id)
    if not voter:
        raise HTTPException(404, "Voter not found")
    await lock_event(db, voter.Event_ID)
    await db.refresh(voter)
    await _validate_links(db, voter.Event_ID, body.Presenter_Project_IDs)
    for key, value in body.model_dump().items():
        setattr(voter, key, value)
    await db.commit()
    await db.refresh(voter)
    return voter


@router.post("/admin/voters/{voter_id}/replace-code")
async def replace_code(
    voter_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    voter = await db.get(Voter, voter_id)
    if not voter:
        raise HTTPException(404, "Voter not found")
    await lock_event(db, voter.Event_ID)
    await db.refresh(voter)
    code, digest = issue_code()
    voter.Code_Hash = digest
    voter.Credential_Version += 1
    voter.Is_Active = True
    await db.commit()
    return {
        "access_code": code,
        "detail": "Old code and sessions invalidated; saved ballots retained.",
    }


@router.post("/admin/voters/{voter_id}/revoke", status_code=204)
async def revoke(
    voter_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    voter = await db.get(Voter, voter_id)
    if not voter:
        raise HTTPException(404, "Voter not found")
    await lock_event(db, voter.Event_ID)
    await db.refresh(voter)
    voter.Is_Active = False
    voter.Credential_Version += 1
    await db.commit()
