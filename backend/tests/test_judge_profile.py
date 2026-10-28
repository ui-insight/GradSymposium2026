"""Judge self-service names preserve identity, work and conflict enforcement."""

import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session
from test_competition import assigned_to, judge_headers, prepared, score_payload
from test_poster_directory import context as poster_context

from app.api.deps import get_current_admin
from app.auth.jwt import create_access_token
from app.config import settings
from app.db.base import Base
from app.db.schema import _ensure_runtime_schema_sync
from app.models.event import Event
from app.models.feedback import Feedback
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.score import Score

context = poster_context


async def work_snapshot(sessions, judge_id):
    async with sessions() as db:
        result = {}
        for model in (Score, Feedback, JudgeAssignment, JudgeConflict):
            rows = (
                await db.execute(
                    sa.select(model.__table__).where(model.Judge_ID == judge_id)
                )
            ).all()
            result[model.__name__] = sorted([tuple(row) for row in rows])
        return result


@pytest.mark.asyncio
async def test_name_confirmation_preserves_identity_work_and_conflicts(context):
    data = await prepared(context)
    client, sessions = data["client"], data["sessions"]
    project = data["projects"][0]
    judge_id = assigned_to(data, project)[0]
    judge = next(j for j in data["judges"] if j["Judge_ID"] == judge_id)
    headers = await judge_headers(data, judge_id)
    assert (
        await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 200
    conflict_project = data["projects"][1]
    assert (
        await client.post(
            "/api/v1/competition/asm/conflicts",
            json={
                "Judge_ID": judge_id,
                "Project_ID": conflict_project["Project_ID"],
                "Reason": "Mentor relationship already reviewed",
            },
        )
    ).status_code == 201
    original = await work_snapshot(sessions, judge_id)
    assert (await client.get("/api/v1/judge/me", headers=headers)).json()[
        "Name_Confirmed_At"
    ] is None

    response = await client.patch(
        "/api/v1/judge/me",
        headers=headers,
        json={"First_Name": judge["First_Name"], "Last_Name": judge["Last_Name"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["Name_Confirmed_At"]
    assert not response.json()["Conflict_Review_Required"]

    response = await client.patch(
        "/api/v1/judge/me",
        headers=headers,
        json={"First_Name": "  María Elena  ", "Last_Name": "  O’Neill-Smith  "},
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["Judge_ID"] == judge_id and saved["Event_ID"] == "asm"
    assert saved["First_Name"] == "María Elena"
    assert saved["Last_Name"] == "O’Neill-Smith"
    assert saved["Name_Confirmed_At"] and saved["Conflict_Review_Required"]
    assert set(saved) == {
        "Judge_ID",
        "Event_ID",
        "First_Name",
        "Last_Name",
        "Name_Confirmed_At",
        "Conflict_Review_Required",
    }
    refreshed = (await client.get("/api/v1/judge/me", headers=headers)).json()
    assert refreshed["First_Name"] == saved["First_Name"]
    assert refreshed["Name_Confirmed_At"] == saved["Name_Confirmed_At"]
    admin = (await client.get(f"/api/v1/judges/{judge_id}")).json()
    assert admin["Access_Code"] == judge["Access_Code"]
    assert admin["Previous_Name"] == f"{judge['First_Name']} {judge['Last_Name']}"
    assert admin["Conflict_Review_Required"]
    assert await work_snapshot(sessions, judge_id) == original
    review = (
        await client.get(f"/api/v1/scores/review/{project['Project_ID']}")
    ).json()["submissions"][0]
    assert review["Judge_Name"] == "María Elena O’Neill-Smith"
    assert (
        await client.post(
            f"/api/v1/judge/projects/{conflict_project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/judge/login", json={"access_code": judge["Access_Code"]}
        )
    ).status_code == 200

    # A second edit preserves the name before the pending corrections.
    assert (
        await client.patch(
            "/api/v1/judge/me",
            headers=headers,
            json={"First_Name": "María", "Last_Name": "Smith"},
        )
    ).status_code == 200
    admin = (await client.get(f"/api/v1/judges/{judge_id}")).json()
    assert admin["Previous_Name"] == f"{judge['First_Name']} {judge['Last_Name']}"
    stale = await client.patch(
        f"/api/v1/judges/{judge_id}",
        json={
            "Conflict_Review_Required": False,
            "Reviewed_Name": "María Elena O’Neill-Smith",
        },
    )
    assert stale.status_code == 409
    response = await client.patch(
        f"/api/v1/judges/{judge_id}",
        json={"Conflict_Review_Required": False, "Reviewed_Name": "María Smith"},
    )
    assert response.status_code == 200
    assert not response.json()["Conflict_Review_Required"]
    assert response.json()["Previous_Name"] is None
    assert await work_snapshot(sessions, judge_id) == original
    # Organizer corrections require the judge to confirm the corrected name.
    response = await client.patch(
        f"/api/v1/judges/{judge_id}", json={"First_Name": "Maria"}
    )
    assert response.status_code == 200
    assert response.json()["Name_Confirmed_At"] is None
    assert response.json()["Conflict_Review_Required"]


@pytest.mark.asyncio
async def test_profile_rejects_invalid_names_and_privilege_changes(context):
    data = await prepared(context)
    client, sessions, app = context
    judge = data["judges"][0]
    headers = await judge_headers(data, judge["Judge_ID"])
    valid = {"First_Name": "Ada", "Last_Name": "Rivera"}
    for changes in (
        {"First_Name": "   "},
        {"Last_Name": "\t\n"},
        {"First_Name": "x" * 101},
        {"Last_Name": None},
        {"First_Name": 42},
        {"Judge_ID": data["judges"][1]["Judge_ID"]},
        {"Event_ID": "elsewhere"},
        {"Is_Active": False},
        {"Access_Code": "NEW123"},
        {"Email": "new@example.org"},
        {"Conflict_Review_Required": False},
        {"Name_Confirmed_At": "2026-10-28"},
    ):
        response = await client.patch(
            "/api/v1/judge/me", headers=headers, json={**valid, **changes}
        )
        assert response.status_code == 422, response.text
    for body in ({}, {"First_Name": "Ada"}):
        assert (
            await client.patch("/api/v1/judge/me", headers=headers, json=body)
        ).status_code == 422
    assert (await client.patch("/api/v1/judge/me", json=valid)).status_code == 401
    for role in ("admin", "voter"):
        assert (
            await client.patch(
                "/api/v1/judge/me",
                json=valid,
                headers={
                    "Authorization": "Bearer " + create_access_token("irrelevant", role)
                },
            )
        ).status_code == 401
    override = app.dependency_overrides.pop(get_current_admin)
    try:
        assert (
            await client.patch(
                f"/api/v1/judges/{data['judges'][1]['Judge_ID']}",
                json=valid,
                headers=headers,
            )
        ).status_code == 401
    finally:
        app.dependency_overrides[get_current_admin] = override
    async with sessions() as db:
        records = (await db.scalars(sa.select(Judge))).all()
        assert all(j.Name_Confirmed_At is None for j in records)
        assert all(not j.Conflict_Review_Required for j in records)
        assert [(j.Judge_ID, j.First_Name, j.Last_Name) for j in records] == [
            (j["Judge_ID"], j["First_Name"], j["Last_Name"]) for j in data["judges"]
        ]
    assert (
        await client.patch(
            f"/api/v1/judges/{judge['Judge_ID']}", json={"Is_Active": False}
        )
    ).status_code == 200
    assert (
        await client.patch("/api/v1/judge/me", headers=headers, json=valid)
    ).status_code == 401


@pytest.mark.parametrize("runtime", [False, True])
def test_existing_judges_gain_profile_fields_without_identity_changes(
    tmp_path, monkeypatch, runtime
):
    database = tmp_path / "judge-profile.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    engine = sa.create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        Base.metadata.create_all(connection)
    with Session(engine) as db:
        db.add(
            Event(
                Event_ID="old",
                Event_Name="Original event",
                Event_Date=datetime.date(2026, 3, 13),
            )
        )
        db.flush()
        db.add(
            Judge(
                Judge_ID="preserved",
                Event_ID="old",
                First_Name="Existing",
                Last_Name="Judge",
                Access_Code="KEEP42",
            )
        )
        db.commit()
    with engine.begin() as connection:
        for column in (
            "Name_Confirmed_At",
            "Previous_Name",
            "Conflict_Review_Required",
        ):
            connection.exec_driver_sql(f'ALTER TABLE "Judge" DROP COLUMN "{column}"')
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.stamp(config, "20261028_five_point_rubric")
    if runtime:
        with engine.begin() as connection:
            _ensure_runtime_schema_sync(connection)
            _ensure_runtime_schema_sync(connection)
    else:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
    with Session(engine) as db:
        judge = db.get(Judge, "preserved")
        assert (
            judge.Event_ID,
            judge.First_Name,
            judge.Last_Name,
            judge.Access_Code,
        ) == ("old", "Existing", "Judge", "KEEP42")
        assert judge.Name_Confirmed_At is None and judge.Previous_Name is None
        assert not judge.Conflict_Review_Required
        judge.Conflict_Review_Required = True
        db.commit()
    if not runtime:
        with pytest.raises(RuntimeError, match="Preserve judge confirmations"):
            command.downgrade(config, "20261028_five_point_rubric")
    engine.dispose()
