"""Admin QR issuance and personal judge activation/recovery."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.auth.jwt import create_access_token, decode_token
from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_invite import JudgeInvite
from app.models.user import User
from app.schemas.judge import JudgeNameUpdate
from app.services.access_code import unique_access_code
from app.services.competition import lock_event
from app.services.judge_checkin import assign_new_judge, invitation_token


def no_cache(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/judge-checkin", tags=["judge check-in"], dependencies=[Depends(no_cache)]
)


class InviteCreate(BaseModel):
    Event_ID: str
    Request_ID: uuid.UUID
    Assignment_Limit: int = Field(default=12, ge=1, le=200)


class InviteToken(BaseModel):
    token: str = Field(min_length=1, max_length=2000)


class InviteClaim(JudgeNameUpdate):
    token: str = Field(min_length=1, max_length=2000)


async def invite_read(db, invite):
    judge = await db.get(Judge, invite.Judge_ID)
    return {
        "Invite_ID": invite.Invite_ID,
        "Judge_ID": judge.Judge_ID,
        "First_Name": judge.First_Name,
        "Last_Name": judge.Last_Name,
        "Is_Active": judge.Is_Active,
        "Activated": invite.Activated_At is not None,
        "Access_Code": judge.Access_Code,
        "token": invitation_token(invite),
        "Assignment_Limit": invite.Assignment_Limit,
        "Issued_At": invite.Issued_At,
        "Assignment_Count": await db.scalar(
            select(func.count())
            .select_from(JudgeAssignment)
            .where(JudgeAssignment.Judge_ID == judge.Judge_ID)
        ),
    }


@router.get("/admin")
async def list_invites(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    invites = list(
        await db.scalars(
            select(JudgeInvite)
            .where(JudgeInvite.Event_ID == event_id)
            .order_by(JudgeInvite.Issued_At.desc())
        )
    )
    return [await invite_read(db, invite) for invite in invites]


@router.post("/admin", status_code=201)
async def create_invite(
    body: InviteCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    event = await db.get(Event, body.Event_ID)
    if not event or not event.Is_Active:
        raise HTTPException(409, "Choose the active conference")
    await lock_event(db, event.Event_ID)
    invite = await db.get(JudgeInvite, str(body.Request_ID))
    if invite:
        if invite.Event_ID != event.Event_ID:
            raise HTTPException(409, "Request already used for another event")
        return await invite_read(db, invite)
    judge = Judge(
        Event_ID=event.Event_ID,
        First_Name="",
        Last_Name="",
        Access_Code=await unique_access_code(db),
        Is_Active=False,
    )
    db.add(judge)
    await db.flush()
    invite = JudgeInvite(
        Invite_ID=str(body.Request_ID),
        Event_ID=event.Event_ID,
        Judge_ID=judge.Judge_ID,
        Assignment_Limit=body.Assignment_Limit,
        Issued_At=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(invite)
    await db.commit()
    return await invite_read(db, invite)


async def resolve_invite(db, token):
    payload = decode_token(token)
    if not payload or payload.get("role") != "judge_invite":
        raise HTTPException(
            401, "Invalid or expired judge QR. Ask the organizer for help."
        )
    invite = await db.get(JudgeInvite, payload.get("sub", ""))
    if not invite:
        raise HTTPException(401, "Invalid judge QR")
    event = await db.get(Event, invite.Event_ID)
    if not event or not event.Is_Active:
        raise HTTPException(409, "This conference is no longer active")
    return invite


def signed_in(judge):
    if not judge.Is_Active:
        raise HTTPException(403, "This judge account is disabled. Ask the organizer.")
    return {
        "activated": True,
        "name_confirmed": judge.Name_Confirmed_At is not None,
        "access_token": create_access_token(judge.Judge_ID, "judge"),
        "Judge_ID": judge.Judge_ID,
        "First_Name": judge.First_Name,
        "Last_Name": judge.Last_Name,
    }


@router.post("/inspect")
async def inspect_invite(body: InviteToken, db: AsyncSession = Depends(get_db)):
    invite = await resolve_invite(db, body.token)
    judge = await db.get(Judge, invite.Judge_ID)
    if invite.Activated_At:
        return signed_in(judge)
    return {"activated": False}


@router.post("/activate")
async def activate_invite(body: InviteClaim, db: AsyncSession = Depends(get_db)):
    invite = await resolve_invite(db, body.token)
    await lock_event(db, invite.Event_ID)
    await db.refresh(invite)
    judge = await db.get(Judge, invite.Judge_ID, populate_existing=True)
    if invite.Activated_At:
        return signed_in(judge)
    judge.First_Name, judge.Last_Name = body.First_Name, body.Last_Name
    judge.Name_Confirmed_At = datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None
    )
    invite.Activated_At = datetime.datetime.now(datetime.timezone.utc)
    judge.Is_Active = True
    await db.flush()
    await assign_new_judge(db, judge, invite.Assignment_Limit)
    await db.commit()
    return signed_in(judge)
