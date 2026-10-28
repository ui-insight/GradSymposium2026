"""Private convention preview and explicit organizer confirmation."""

import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.poster_session import PosterSession
from app.schemas.poster_session import SessionApply, SessionProposal
from app.services.poster_sessions import (
    convention,
    event_convention,
    poster_location,
    valid_poster_number,
)
from app.services.project_numbering import lock_event_numbers
from app.services.roster_review import digest, final_roster_ready, load_roster

router = APIRouter(prefix="/poster-sessions", tags=["poster sessions"])


async def preview(db, event_id, proposal=None):
    event, projects, history, latest, signoff = await load_roster(db, event_id)
    current = await event_convention(db, event_id)
    config = proposal or current
    rows = [
        {
            "Project_ID": p.Project_ID,
            "Project_Number": p.Project_Number,
            "Project_Title": p.Project_Title,
            "Presenter_Display_Name": p.Presenter_Display_Name
            or f"{p.Presenter_First_Name} {p.Presenter_Last_Name}".strip(),
            "Table_Number": p.Table_Number,
            "Is_Active": p.Is_Active,
            **poster_location(p, config),
            "Needs_Review": bool(
                p.Is_Active and not valid_poster_number(p.Project_Number)
            ),
        }
        for p in projects
    ]
    context = digest(
        [
            convention(current),
            convention(config),
            [
                (
                    p.Project_ID,
                    p.Project_Number,
                    p.Project_Title,
                    p.Presenter_Display_Name,
                    p.Presenter_First_Name,
                    p.Presenter_Last_Name,
                    p.Table_Number,
                    p.Is_Active,
                )
                for p in projects
            ],
            [(h.Decision_ID, h.Source_Context) for h in history],
            signoff.Signoff_ID if signoff else None,
        ]
    )
    return {
        "Event_ID": event_id,
        "Event_Name": event.Event_Name,
        "Configuration": convention(current),
        "Confirmation": {
            "By": current.Confirmed_By,
            "At": current.Confirmed_At,
            "Reference": current.Reference,
        }
        if current
        else None,
        "Proposal": convention(config),
        "Context": context,
        "Rows": rows,
        "Final_Roster_Ready": await final_roster_ready(db, event_id),
    }


@router.get("/{event_id}")
async def get_preview(
    event_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)
):
    return await preview(db, event_id)


@router.post("/{event_id}/preview")
async def propose(
    event_id: str,
    body: SessionProposal,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return await preview(db, event_id, body)


@router.put("/{event_id}")
async def apply(
    event_id: str,
    body: SessionApply,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    await lock_event_numbers(db, event_id)
    state = await preview(db, event_id, body)
    if body.Context != state["Context"]:
        raise HTTPException(409, "Roster or mapping changed. Preview again")
    if not state["Final_Roster_Ready"]:
        raise HTTPException(
            409, "Complete final roster review before applying sessions"
        )
    if (
        any(row["Needs_Review"] for row in state["Rows"])
        and not body.Unassigned_Numbers_Confirmed
    ):
        raise HTTPException(409, "Confirm unexpected numbers will remain unassigned")
    config = await event_convention(db, event_id)
    if config is None:
        config = PosterSession(Event_ID=event_id)
        db.add(config)
    for key, value in convention(body).items():
        setattr(config, key, value)
    config.Reference = body.Reference
    config.Confirmed_By = admin.Username
    config.Confirmed_At = datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None
    )
    await db.commit()
    return await preview(db, event_id)
