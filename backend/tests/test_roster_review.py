"""Final inclusion evidence, permanent numbers and exact-roster publication."""

import csv
import datetime
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from test_competition import assigned_to, judge_headers, prepared, score_payload
from test_poster_directory import context as poster_context
from test_poster_directory import create, directory, publish, source_fixture

from app.api.deps import get_current_admin
from app.auth.jwt import create_access_token
from app.config import settings
from app.db.base import Base
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.roster_review import RosterDecision, RosterSignoff
from app.models.score import Score
from app.services.asm_roster import prepare_submissions, stage_submissions

context = poster_context


async def staged(context):
    client, sessions, _ = context
    values = source_fixture()
    for index, row in enumerate(values[1:]):
        row[0] = datetime.datetime(2026, 10, index + 1, 12, 0)
    submissions = prepare_submissions(
        values, "private-source.xlsx", "source-hash", "Responses"
    )
    async with sessions() as db:
        await stage_submissions(db, "asm", submissions)
        await db.commit()
    return client


async def state(client):
    response = await client.get("/api/v1/roster-review/asm")
    assert response.status_code == 200, response.text
    return response.json()


def target(row):
    return {"Project_ID": row["Project_ID"], "Context": row["Context"]}


async def decide(client, rows, action="accept", **changes):
    return await client.post(
        "/api/v1/roster-review/asm/decisions",
        json={
            "Action": action,
            "Reason": "Organizer confirmed final list",
            "Targets": [target(r) for r in rows],
            **changes,
        },
    )


async def resolved(client):
    current = await state(client)
    older, later, talk, joint = current["Rows"]
    response = await client.post(
        "/api/v1/roster-review/asm/duplicates",
        json={
            "Keep": target(later),
            "Withdraw": target(older),
            "Reason": "Paul: keep the later abstract; timestamps checked",
            "Source_Verified": True,
        },
    )
    assert response.status_code == 200, response.text
    response = await decide(client, [talk, joint], Talk_Only_Confirmed=True)
    assert response.status_code == 200, response.text
    return response.json()


async def sign(client, current, **changes):
    return await client.post(
        "/api/v1/roster-review/asm/signoff",
        json={
            "Context": current["Context"],
            "Accepted_Count": current["Counts"]["Accepted"],
            "Source_Count": current["Counts"]["Source"],
            "Reference": "Organizer final list confirmed",
            "Final_Changes_Confirmed": True,
            "Preview_Reviewed": True,
            **changes,
        },
    )


@pytest.mark.asyncio
async def test_complete_source_reconciliation_signoff_and_private_preview(context):
    client = await staged(context)
    initial = await state(client)
    assert initial["Counts"] == {
        "Total": 4,
        "Source": 4,
        "Additions": 0,
        "Accepted": 0,
        "Withdrawn": 0,
        "Pending": 4,
        "Changed": 0,
    }
    ids = [(r["Project_ID"], r["Project_Number"]) for r in initial["Rows"]]
    talk = initial["Rows"][2]
    assert (await decide(client, [talk])).status_code == 409
    current = await resolved(client)
    assert (
        current["Counts"]["Accepted"] == 3
        and current["Counts"]["Withdrawn"] == 1
        and not current["Blockers"]
    )
    assert [(r["Project_ID"], r["Project_Number"]) for r in current["Rows"]] == ids
    older, later, talk, joint = current["Rows"]
    assert older["Decision"]["Superseded_By"] == later["Project_ID"]
    assert older["Decision"]["Snapshot"]["Source"]["source_row"] == 2
    assert all(
        r["Judging_Eligible"] is None and r["Voting_Eligible"] is None
        for r in current["Rows"]
    )
    assert (
        current["Preview"]["posters"][-1]["Presenter_Display_Name"]
        == "Jo Chen, Pat Rivera"
    )
    assert "alex@example.edu" not in str(
        current["Preview"]
    ) and "Advisor_Name" not in str(current["Preview"])
    assert (await publish(client)).status_code == 409
    response = await sign(client, current)
    assert response.status_code == 200 and response.json()["Signoff"]["Current"]
    assert (await directory(client))["posters"] == []  # Signing does not publish.
    assert (await publish(client)).status_code == 200
    assert (await directory(client))["posters"] == current["Preview"]["posters"]
    # Competition configuration is separate from acceptance/publication.
    response = await client.patch(
        f"/api/v1/projects/{joint['Project_ID']}",
        json={"Judging_Eligible": True, "Voting_Eligible": False},
    )
    assert response.status_code == 200 and response.json()["Is_Published"]
    assert (await state(client))["Signoff"]["Current"]
    assert len((await directory(client))["posters"]) == 3
    report = (await client.get("/api/v1/roster-review/asm/report")).json()["content"]
    assert (
        "Accepted: 3" in report
        and "Source: 4" in report
        and "Organizer final list confirmed" in report
    )
    assert "example.edu" not in report and "private-source.xlsx" not in report
    assert (
        await client.delete(f"/api/v1/projects/{older['Project_ID']}")
    ).status_code == 409


@pytest.mark.asyncio
async def test_corrections_and_late_arrivals_invalidate_signoff_without_renumbering(
    context,
):
    client = await staged(context)
    current = await resolved(client)
    assert (await sign(client, current)).status_code == 200
    await publish(client)
    joint = current["Rows"][-1]
    response = await client.patch(
        f"/api/v1/roster-review/asm/{joint['Project_ID']}/correction",
        json={
            "Context": joint["Context"],
            "Reason": "Final co-presenter correction",
            "Project_Title": "Corrected full title",
            "Presenter_Display_Name": "Jo Chen, Pat Rivera, Alex García",
            "Institution": "Idaho",
            "Table_Number": None,
        },
    )
    assert response.status_code == 200, response.text
    current = response.json()
    updated = current["Rows"][-1]
    assert updated["Advisor_Name"] == joint["Advisor_Name"]
    assert (
        updated["Project_Number"] == joint["Project_Number"]
        and updated["Acceptance"] == "pending"
    )
    assert (
        len(updated["History"]) == 2
        and updated["History"][0]["Snapshot"]["Presenter_Name"] == "Jo Chen, Pat Rivera"
    )
    assert (
        not current["Signoff"]["Current"] and (await directory(client))["posters"] == []
    )
    assert (await decide(client, [updated])).status_code == 200
    current = await state(client)
    assert (await sign(client, current)).status_code == 200
    late = await create(
        client, Project_Title="New late poster", Presenter_Display_Name="New Person"
    )
    assert late["Project_Number"] == "P-005"
    current = await state(client)
    assert (
        current["Counts"]["Source"] == 4
        and current["Counts"]["Additions"] == 1
        and current["Counts"]["Pending"] == 1
    )
    assert (
        not current["Signoff"]["Current"] and (await publish(client)).status_code == 409
    )
    # Even a legacy direct edit must invalidate exact-content sign-off.
    assert (
        await client.patch(
            f"/api/v1/projects/{joint['Project_ID']}",
            json={"Institution": "Corrected university"},
        )
    ).status_code == 200
    changed = next(
        r
        for r in (await state(client))["Rows"]
        if r["Project_ID"] == joint["Project_ID"]
    )
    assert changed["Changed"] and changed["Acceptance"] == "pending"


def csv_file(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


async def upload(client, content, preview=None):
    return await client.post(
        f"/api/v1/roster-review/asm/changes-csv?dry_run={str(preview is None).lower()}",
        files={"file": ("changes.csv", content, "text/csv")},
        data={"context": preview["Context"]} if preview else {},
    )


@pytest.mark.asyncio
async def test_final_change_csv_preview_is_atomic_stale_safe_and_reserves_new_numbers(
    context,
):
    client = await staged(context)
    template = (await client.get("/api/v1/roster-review/asm/template")).json()[
        "content"
    ]
    rows = list(csv.DictReader(io.StringIO(template)))
    assert all(
        None not in row and all(v is not None for v in row.values()) for row in rows
    )
    rows[-1].update(
        Action="correct",
        Title="Final revised joint title",
        Reason="Organizer correction",
    )
    addition = {key: "" for key in rows[-1]}
    addition.update(
        Action="add",
        Title="Late new poster",
        Presenter_Display_Name="New Presenter, Co Presenter",
        Reason="Organizer final addition",
    )
    content = csv_file([rows[-1], addition])
    preview = (await upload(client, content)).json()
    assert preview["Errors"] == [] and preview["Rows"][-1]["Project_Number"] == "P-005"
    assert len((await state(client))["Rows"]) == 4
    response = await upload(client, content, preview)
    assert response.status_code == 200 and response.json()["Applied"]
    current = await state(client)
    assert len(current["Rows"]) == 5 and current["Rows"][-1]["Acceptance"] == "pending"
    assert current["Rows"][-1]["Presenter_Name"] == "New Presenter, Co Presenter"
    assert current["Rows"][3]["Project_Title"] == "Final revised joint title"
    assert (await upload(client, content)).json()[
        "Errors"
    ]  # Re-upload cannot invent duplicates.
    stale_rows = list(
        csv.DictReader(
            io.StringIO(
                (await client.get("/api/v1/roster-review/asm/template")).json()[
                    "content"
                ]
            )
        )
    )
    stale_rows[-1].update(Action="accept", Reason="Confirmed addition")
    content = csv_file([stale_rows[-1]])
    preview = (await upload(client, content)).json()
    await create(
        client,
        Project_Title="Concurrent addition",
        Presenter_Display_Name="Another Person",
    )
    assert (await upload(client, content, preview)).status_code == 409
    assert (await state(client))["Rows"][4]["Acceptance"] == "pending"
    invalid = {**addition, "Action": "unknown"}
    result = (await upload(client, csv_file([addition, invalid]))).json()
    assert (
        result["Errors"]
        and (await upload(client, csv_file([addition, invalid]), result)).status_code
        == 422
    )
    assert len((await state(client))["Rows"]) == 6


@pytest.mark.asyncio
async def test_duplicate_direction_stale_context_and_batch_atomicity(context):
    client = await staged(context)
    initial = await state(client)
    older, later, talk, joint = initial["Rows"]
    assert (
        await client.post(
            "/api/v1/roster-review/asm/duplicates",
            json={
                "Keep": target(older),
                "Withdraw": target(later),
                "Reason": "Wrong direction",
                "Source_Verified": True,
            },
        )
    ).status_code == 409
    assert (await decide(client, [joint, older])).status_code == 409
    assert all(not r["History"] for r in (await state(client))["Rows"])
    assert (await decide(client, [talk], "withdraw")).status_code == 200
    assert (await decide(client, [talk], "reopen")).status_code == 409  # Old token.
    fresh = (await state(client))["Rows"][2]
    assert (await decide(client, [fresh], "reopen")).status_code == 200
    assert (await state(client))["Rows"][2]["Acceptance"] == "pending"


@pytest.mark.asyncio
async def test_withdrawal_preserves_existing_scores_and_reserved_numbers(context):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    headers = await judge_headers(data, assigned_to(data, project)[0])
    assert (
        await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 200
    row = next(
        r
        for r in (await state(client))["Rows"]
        if r["Project_ID"] == project["Project_ID"]
    )
    assert (await decide(client, [row], "withdraw")).status_code == 200
    async with data["sessions"]() as db:
        assert await db.scalar(sa.select(sa.func.count()).select_from(Score)) == 2
        assert not await db.scalar(
            sa.select(JudgeAssignment.Assignment_ID).where(
                JudgeAssignment.Project_ID == project["Project_ID"]
            )
        )
        old = await db.get(Project, project["Project_ID"])
        assert old.Project_Number == project["Project_Number"] and not old.Is_Active
    response = await client.post(
        "/api/v1/projects/",
        json={
            "Event_ID": "asm",
            "Category": "Poster",
            "Project_Number": project["Project_Number"],
            "Project_Title": "Reused",
            "Presenter_Display_Name": "Other Person",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signoff_counts_role_scope_and_validation(context):
    client = await staged(context)
    current = await resolved(client)
    assert (await sign(client, current, Accepted_Count=99)).status_code == 409
    assert (await sign(client, current, Source_Count=99)).status_code == 409
    assert (await sign(client, current, Preview_Reviewed=False)).status_code == 422
    assert (
        await sign(client, current, Final_Changes_Confirmed=False)
    ).status_code == 422
    assert (await client.get("/api/v1/roster-review/missing")).status_code == 404
    row = current["Rows"][-1]
    assert (
        await client.patch(
            f"/api/v1/roster-review/asm/{row['Project_ID']}/correction",
            json={
                "Context": row["Context"],
                "Reason": "No renumbering",
                "Project_Title": "Title",
                "Presenter_Display_Name": "Name",
                "Project_Number": "P-777",
            },
        )
    ).status_code == 422
    _, _, app = context
    override = app.dependency_overrides.pop(get_current_admin)
    try:
        for role in (None, "judge", "voter"):
            headers = (
                {"Authorization": "Bearer " + create_access_token("other", role)}
                if role
                else {}
            )
            assert (
                await client.get("/api/v1/roster-review/asm", headers=headers)
            ).status_code == 401
            assert (
                await client.get("/api/v1/roster-review/asm/report", headers=headers)
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/roster-review/asm/decisions",
                    headers=headers,
                    json={
                        "Action": "accept",
                        "Reason": "Attempt",
                        "Targets": [target(row)],
                    },
                )
            ).status_code == 401
    finally:
        app.dependency_overrides[get_current_admin] = override


def test_final_roster_migration_repeats_and_guards_saved_evidence(
    tmp_path, monkeypatch
):
    database = tmp_path / "roster.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    engine = sa.create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        Base.metadata.create_all(connection)
        RosterSignoff.__table__.drop(connection)
        RosterDecision.__table__.drop(connection)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.stamp(config, "20261028_mentor_review")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                'INSERT INTO "Roster_Decision" ("Project_ID", "Decision", "Reason", '
                '"Source_Context", "Snapshot", "Recorded_By", "Recorded_At") VALUES '
                "('poster', 'pending', 'Ask organizer', 'context', '{}', "
                "'test', CURRENT_TIMESTAMP)"
            )
        )
    with pytest.raises(RuntimeError, match="Archive final roster"):
        command.downgrade(config, "20261028_mentor_review")
    engine.dispose()
