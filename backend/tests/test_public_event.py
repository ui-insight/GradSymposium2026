"""Conference branding is public independently of unpublished poster records."""

import datetime

import pytest
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.config import settings
from app.models.event import Event

context = poster_context


@pytest.mark.asyncio
async def test_conference_details_without_roster_publication(context, monkeypatch):
    client, sessions, _ = context
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "public_draft_preview", False)
    await create(client, Presenter_Email="private@example.org")
    async with sessions() as db:
        event = await db.get(Event, "asm")
        event.Event_End_Date = datetime.date(2026, 11, 1)
        event.Location = "Conference venue"
        event.Description = "Private operator notes"
        assert not event.Public_Poster_Lookup_Enabled
        await db.commit()
    response = await client.get(
        "/api/v1/public/event", headers={"Authorization": "Bearer expired-token"}
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "Event_Name": "ASM 2026",
        "Event_Date": "2026-10-31",
        "Event_End_Date": "2026-11-01",
        "Location": "Conference venue",
    }
    directory = (await client.get("/api/v1/public/posters")).json()
    assert directory["posters"] == [] and directory["event"] is None
    async with sessions() as db:
        assert not (await db.get(Event, "asm")).Public_Poster_Lookup_Enabled


@pytest.mark.asyncio
@pytest.mark.parametrize("active_count", [0, 2])
async def test_missing_or_ambiguous_active_event_returns_no_details(
    context, active_count
):
    client, sessions, _ = context
    async with sessions() as db:
        (await db.get(Event, "asm")).Is_Active = active_count == 2
        if active_count == 2:
            db.add(
                Event(
                    Event_ID="other",
                    Event_Name="Other event",
                    Event_Date=datetime.date(2026, 10, 31),
                    Is_Active=True,
                )
            )
        await db.commit()
    response = await client.get("/api/v1/public/event")
    assert response.status_code == 200 and response.json() is None
