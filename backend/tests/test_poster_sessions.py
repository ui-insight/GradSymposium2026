"""Confirmed conventions use permanent identities across public/judge views."""

import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from test_competition import judge_headers, prepared
from test_poster_directory import context as poster_context
from test_poster_directory import create, directory, publish
from test_roster_review import resolved, sign, staged, state

from app.api.deps import get_current_admin
from app.models.poster_session import PosterSession
from app.models.project import Project
from app.services.poster_sessions import poster_location

context = poster_context
path = "/api/v1/poster-sessions/asm"
proposal = {
    "Odd_Session": "II",
    "Session_I_Time": "Saturday, October 31, 10–11 AM Pacific",
    "Session_II_Time": "Saturday, October 31, 2–3 PM Pacific",
}


async def preview(client, **changes):
    response = await client.post(path + "/preview", json={**proposal, **changes})
    assert response.status_code == 200, response.text
    return response.json()


async def apply(client, planned, **changes):
    return await client.put(
        path,
        json={
            **proposal,
            "Context": planned["Context"],
            "Reference": "Synthetic Paul confirmation",
            "Organizer_Confirmed": True,
            **changes,
        },
    )


@pytest.mark.asyncio
async def test_unconfigured_preview_is_read_only_and_uses_suffixes(context):
    client, sessions, _ = context
    for number in ("P-001", "P-003", "P-100", "P-108", "P-109"):
        await create(client, Project_Number=number, Table_Number="North wall")
    withdrawn = await create(client, Project_Number="P-002")
    assert (
        await client.post(f"/api/v1/projects/{withdrawn['Project_ID']}/withdraw")
    ).status_code == 200
    before = (await client.get(path)).json()
    assert before["Configuration"] is None
    assert all(row["Poster_Session"] is None for row in before["Rows"])
    assert all(row["Board_Label"] == row["Project_Number"] for row in before["Rows"])
    planned = await preview(client)
    by_number = {r["Project_Number"]: r for r in planned["Rows"]}
    for number in ("P-001", "P-003", "P-109"):
        assert by_number[number]["Poster_Session"] == "Session II"
        assert by_number[number]["Poster_Session_Time"] == proposal["Session_II_Time"]
    for number in ("P-002", "P-100", "P-108"):
        assert by_number[number]["Poster_Session"] == "Session I"
    assert by_number["P-108"]["Board_Label"] == "P-108"
    assert by_number["P-108"]["Table_Number"] == "North wall"
    assert not by_number["P-002"]["Is_Active"]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PosterSession)) == 0
    assert (await client.get(path)).json() == before
    reverse = await preview(client, Odd_Session="I")
    assert reverse["Rows"][0]["Poster_Session"] == "Session I"
    assert (await apply(client, planned, Organizer_Confirmed=False)).status_code == 422
    assert (
        await client.post(path + "/preview", json={**proposal, "Session_I_Time": "  "})
    ).status_code == 422


@pytest.mark.asyncio
async def test_apply_stale_guard_exceptions_and_late_additions(context):
    client, sessions, _ = context
    await create(client, Project_Number="P-108")
    planned = await preview(client)
    await create(client, Project_Number="P-109")
    assert (await apply(client, planned)).status_code == 409
    unexpected = await create(client, Project_Number="BOARD-X")
    planned = await preview(client)
    assert any(r["Needs_Review"] for r in planned["Rows"])
    assert (await apply(client, planned)).status_code == 409
    response = await apply(client, planned, Unassigned_Numbers_Confirmed=True)
    assert response.status_code == 200, response.text
    rows = response.json()["Rows"]
    assert (
        next(r for r in rows if r["Project_ID"] == unexpected["Project_ID"])[
            "Poster_Session"
        ]
        is None
    )
    late = await create(client)
    assert late["Project_Number"] == "P-110"
    current = (await client.get(path)).json()
    row = next(r for r in current["Rows"] if r["Project_ID"] == late["Project_ID"])
    assert row["Poster_Session"] == "Session I"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PosterSession)) == 1
        assert (await db.get(Project, late["Project_ID"])).Table_Number is None


@pytest.mark.asyncio
async def test_final_review_gate_and_directory_signoff_invalidation(context):
    client = await staged(context)
    planned = await preview(client)
    assert not planned["Final_Roster_Ready"]
    assert (await apply(client, planned)).status_code == 409
    ready = await resolved(client)
    assert (await sign(client, ready)).status_code == 200
    unconfigured_report = (await client.get("/api/v1/roster-review/asm/report")).json()[
        "content"
    ]
    assert "Board P-002; Session to be confirmed" in unconfigured_report
    assert "; None" not in unconfigured_report
    assert (await publish(client)).status_code == 200
    planned = await preview(client)
    assert planned["Final_Roster_Ready"]
    response = await apply(client, planned)
    assert response.status_code == 200, response.text
    assert not response.json()["Final_Roster_Ready"]
    assert (await directory(client))["posters"] == []
    reviewed = await state(client)
    assert not reviewed["Signoff"]["Current"]
    assert all(
        p["Board_Label"] == p["Project_Number"] for p in reviewed["Preview"]["posters"]
    )
    assert (await sign(client, reviewed)).status_code == 200
    public = await directory(client)
    assert len(public["posters"]) == 3
    assert public["posters"][0]["Poster_Session"] == "Session I"
    assert "Reference" not in str(public)
    assert "Advisor_Name" not in str(public)
    report = (await client.get("/api/v1/roster-review/asm/report")).json()["content"]
    assert "Board P-002; Session I;" in report


@pytest.mark.asyncio
async def test_judge_and_public_share_convention_and_admin_boundary(context):
    data = await prepared(context)
    client, sessions, app = context
    planned = await preview(client)
    assert (await apply(client, planned)).status_code == 200
    headers = await judge_headers(data, data["judges"][0]["Judge_ID"])
    projects = (await client.get("/api/v1/judge/projects", headers=headers)).json()
    assert projects
    for project in projects:
        detail = (
            await client.get(
                f"/api/v1/judge/projects/{project['Project_ID']}", headers=headers
            )
        ).json()
        for key in ("Board_Label", "Poster_Session", "Poster_Session_Time"):
            assert detail[key] == project[key]
        assert project["Board_Label"] == project["Project_Number"]
    app.dependency_overrides.pop(get_current_admin)
    for token in ({}, headers):
        for method, suffix in (("get", ""), ("post", "/preview"), ("put", "")):
            kwargs = {} if method == "get" else {"json": proposal}
            assert (
                await getattr(client, method)(path + suffix, headers=token, **kwargs)
            ).status_code == 401


@pytest.mark.parametrize("number", ["P-000", "P-1x", "p-001", "1", "P-١", "P-001 "])
def test_unexpected_number_is_never_guessed(number):
    assert (
        poster_location(
            SimpleNamespace(Category="Poster", Project_Number=number),
            SimpleNamespace(**proposal),
        )["Poster_Session"]
        is None
    )


def test_migration_preserves_rows_and_refuses_populated_downgrade(
    tmp_path, monkeypatch
):
    from pathlib import Path

    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config

    url = f"sqlite:///{tmp_path / 'migration.db'}"
    from app.config import settings

    monkeypatch.setattr(
        settings, "database_url", url.replace("sqlite://", "sqlite+aiosqlite://")
    )
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "migrations")
    )
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    engine = sa.create_engine(url)
    with engine.begin() as db:
        assert db.scalar(sa.text('SELECT count(*) FROM "Poster_Session"')) == 0
        db.execute(
            sa.text(
                'INSERT INTO "Poster_Session" '
                "VALUES (:id, :odd, :one, :two, :ref, :by, :at)"
            ),
            dict(
                id="event",
                odd="I",
                one="Confirmed I",
                two="Confirmed II",
                ref="Synthetic",
                by="admin",
                at=datetime.datetime.now(),
            ),
        )
    with pytest.raises(RuntimeError, match="Archive confirmed poster sessions"):
        command.downgrade(config, "20261028_final_roster")
    engine.dispose()
