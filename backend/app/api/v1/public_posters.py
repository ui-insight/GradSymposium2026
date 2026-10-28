"""Allowlisted poster directory, with an explicitly enabled dev draft preview."""

import re

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.models.event import Event
from app.models.project import Project
from app.schemas.public_poster import PublicEvent, PublicPoster, PublicPosterDirectory
from app.services.roster_review import final_roster_ready

router = APIRouter(prefix="/public", tags=["public posters"])


@router.get("/posters", response_model=PublicPosterDirectory)
async def poster_directory(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    events = list(await db.scalars(select(Event).where(Event.Is_Active.is_(True))))
    # Ambiguous event configuration must never expose the wrong roster.
    draft_preview = settings.dev_mode and settings.public_draft_preview
    if len(events) != 1 or (
        not draft_preview and not events[0].Public_Poster_Lookup_Enabled
    ):
        return PublicPosterDirectory()
    event = events[0]
    if not draft_preview and not await final_roster_ready(db, event.Event_ID):
        return PublicPosterDirectory()
    statement = select(Project).where(
        Project.Event_ID == event.Event_ID,
        Project.Category == "Poster",
        Project.Is_Active.is_(True),
    )
    if not draft_preview:
        statement = statement.where(
            Project.Is_Published.is_(True),
            Project.Roster_Review_Required.is_(False),
        )
    projects = await db.scalars(statement)

    def number_key(project):
        return tuple(
            (0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r"(\d+)", project.Project_Number)
        )

    return PublicPosterDirectory(
        is_draft_preview=draft_preview,
        event=PublicEvent.model_validate(event),
        posters=[
            PublicPoster(
                Project_Number=project.Project_Number,
                Project_Title=project.Project_Title,
                Presenter_Display_Name=project.Presenter_Display_Name
                or " ".join(
                    (project.Presenter_First_Name, project.Presenter_Last_Name)
                ).strip(),
                Institution=project.Institution,
                Table_Number=project.Table_Number,
            )
            for project in sorted(projects, key=number_key)
        ],
    )
