"""Serialize number issuance per event and permanently reserve issued numbers."""

import re

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.project import Project
from app.models.project_number_reservation import ProjectNumberReservation


async def lock_event_numbers(db: AsyncSession, event_id: str) -> None:
    # A write lock works on SQLite as well as PostgreSQL. Take it before reads.
    result = await db.execute(
        update(Event)
        .where(Event.Event_ID == event_id)
        .values(Is_Active=Event.Is_Active)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=404, detail="Event not found")

    reservations = await db.scalars(
        select(ProjectNumberReservation.Project_Number).where(
            ProjectNumberReservation.Event_ID == event_id
        )
    )
    reserved = set(reservations)
    projects = await db.scalars(select(Project).where(Project.Event_ID == event_id))
    for project in projects:
        if project.Project_Number not in reserved:
            db.add(
                ProjectNumberReservation(
                    Event_ID=event_id,
                    Project_Number=project.Project_Number,
                    Project_ID=project.Project_ID,
                )
            )
            reserved.add(project.Project_Number)
    await db.flush()


async def reserve_number(
    db: AsyncSession,
    event_id: str,
    project_id: str,
    category: str,
    requested: str | None = None,
) -> str:
    """Caller must hold the event number lock until commit or rollback."""
    reserved = set(
        await db.scalars(
            select(ProjectNumberReservation.Project_Number).where(
                ProjectNumberReservation.Event_ID == event_id
            )
        )
    )
    if requested:
        number = requested.strip().upper()
        numeric = re.fullmatch(r"([PA])-(\d+)", number)
        equivalent = numeric and any(
            match
            and match.group(1) == numeric.group(1)
            and int(match.group(2)) == int(numeric.group(2))
            for issued_number in reserved
            if (match := re.fullmatch(r"([PA])-(\d+)", issued_number))
        )
        if number in reserved or equivalent:
            raise ValueError(f"Number {number} has already been issued")
    else:
        prefix = "P" if category == "Poster" else "A"
        issued = [
            int(match.group(1))
            for number in reserved
            if (match := re.fullmatch(rf"{prefix}-(\d+)", number))
        ]
        number = f"{prefix}-{max(issued, default=0) + 1:03d}"
    if not number or len(number) > 20:
        raise ValueError("Poster numbers must contain 1–20 characters")
    db.add(
        ProjectNumberReservation(
            Event_ID=event_id, Project_Number=number, Project_ID=project_id
        )
    )
    await db.flush()
    return number
