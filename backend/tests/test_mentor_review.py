"""Reconcile explicit identities without inferring relationships from name matches."""

import csv
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from test_competition import assigned_to, judge_headers, prepared, score_payload
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.api.deps import get_current_admin
from app.auth.jwt import create_access_token
from app.config import settings
from app.db.base import Base
from app.models.competition import CompetitionSettings
from app.models.mentor_review import MentorReview
from app.models.score import Score

context = poster_context


async def workspace(data, judge_id):
    response = await data["client"].get(
        f"/api/v1/mentor-review/asm?judge_id={judge_id}"
    )
    assert response.status_code == 200, response.text
    return response.json()


async def decide(data, judge_id, project_id, decision, note="Confirmed with Paul"):
    state = await workspace(data, judge_id)
    row = next(p for p in state["Projects"] if p["Project_ID"] == project_id)
    return await data["client"].put(
        f"/api/v1/mentor-review/asm/{judge_id}/{project_id}",
        json={"Context": row["Context"], "Decision": decision, "Note": note},
    )


def csv_file(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


async def upload(client, kind, content, preview=None):
    return await client.post(
        f"/api/v1/mentor-review/asm/imports/{kind}"
        f"?dry_run={str(preview is None).lower()}",
        files={"file": ("review.csv", content, "text/csv")},
        data={"context": preview["Context"]} if preview else {},
    )


@pytest.mark.asyncio
async def test_conflict_review_removes_assignment_and_blocks_all_scoring_paths(context):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    judge_id = assigned_to(data, project)[0]
    headers = await judge_headers(data, judge_id)
    async with data["sessions"]() as db:
        rules = await db.get(CompetitionSettings, "asm")
        rules.Assignment_Only = False
        await db.commit()
    assert (
        await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 200
    initial = await workspace(data, judge_id)
    assert all(p["Status"] == "unreviewed" for p in initial["Projects"])
    assert all(p["Advisor_Name"] is None for p in initial["Projects"])
    assert "Access_Code" not in initial["Judges"][0]
    response = await decide(
        data, judge_id, project["Project_ID"], "conflict", "Paul confirmed co-mentor"
    )
    assert response.status_code == 200, response.text
    state = response.json()
    row = next(p for p in state["Projects"] if p["Project_ID"] == project["Project_ID"])
    assert row["Status"] == "conflict" and row["Has_Scores"] and not row["Assigned"]
    assert row["Conflict_Reason"] == "Paul confirmed co-mentor"
    assert row["Reviewed_By"] == "test" and row["Reviewed_At"]
    assert state["Assignment_Shortages"]
    assert (
        await client.post(
            "/api/v1/assignments/",
            json={"Judge_ID": judge_id, "Project_ID": project["Project_ID"]},
        )
    ).status_code == 409
    assert (
        await client.post(
            "/api/v1/assignments/auto",
            json={"Event_ID": "asm", "Judges_Per_Project": 3},
        )
    ).json()["shortages"]
    assignments = (await client.get("/api/v1/assignments/?event_id=asm")).json()
    assert not any(
        a["Judge_ID"] == judge_id and a["Project_ID"] == project["Project_ID"]
        for a in assignments
    )
    assert (
        await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 403
    async with data["sessions"]() as db:
        assert await db.scalar(sa.select(sa.func.count()).select_from(Score)) == 2
    assert (
        await decide(data, judge_id, project["Project_ID"], "clear")
    ).status_code == 409
    assert (
        await client.delete(f"/api/v1/projects/{project['Project_ID']}")
    ).status_code == 409
    assert (await client.delete(f"/api/v1/judges/{judge_id}")).status_code == 409


@pytest.mark.asyncio
async def test_uncertainty_stale_evidence_and_final_roster_gate_name_review(context):
    data = await prepared(context)
    client, judge = data["client"], data["judges"][0]
    judge_id = judge["Judge_ID"]
    first = data["projects"][0]["Project_ID"]
    assert (
        await decide(
            data,
            judge_id,
            first,
            "needs_input",
            "Initials only; ask Paul about co-mentors",
        )
    ).status_code == 200
    state = await workspace(data, judge_id)
    assert state["Remaining"] == 3 and state["Projects"][0]["Status"] == "needs_input"
    for project in data["projects"]:
        assert (
            await decide(
                data,
                judge_id,
                project["Project_ID"],
                "clear",
                "Paul confirmed no mentor/other conflict despite missing PI",
            )
        ).status_code == 200
    state = await workspace(data, judge_id)
    assert not state["Completion_Blockers"]
    stale_context = state["Projects"][0]["Context"]
    assert (
        await client.patch(
            f"/api/v1/projects/{first}", json={"Advisor_Name": "New lab / Dr A. Mentor"}
        )
    ).status_code == 200
    response = await client.put(
        f"/api/v1/mentor-review/asm/{judge_id}/{first}",
        json={"Context": stale_context, "Decision": "clear", "Note": "Old details"},
    )
    assert response.status_code == 409
    state = await workspace(data, judge_id)
    assert state["Projects"][0]["Status"] == "stale"
    assert (await decide(data, judge_id, first, "clear")).status_code == 200
    state = await workspace(data, judge_id)
    await create(client, Project_Title="New pending poster")
    assert (
        await client.post(
            f"/api/v1/mentor-review/asm/{judge_id}/complete",
            json={"Context": state["Context"]},
        )
    ).status_code == 409
    assert any(
        "roster/eligibility" in value
        for value in (await workspace(data, judge_id))["Completion_Blockers"]
    )
    assert (
        await client.patch(
            f"/api/v1/judges/{judge_id}", json={"First_Name": "Corrected"}
        )
    ).status_code == 200
    state = await workspace(data, judge_id)
    assert all(p["Status"] == "stale" for p in state["Projects"][:3])


@pytest.mark.asyncio
async def test_finish_name_review_only_after_current_relationships_resolved(context):
    data = await prepared(context)
    client, judge_id = data["client"], data["judges"][0]["Judge_ID"]
    await client.patch(f"/api/v1/judges/{judge_id}", json={"First_Name": "Corrected"})
    for project in data["projects"]:
        assert (
            await decide(data, judge_id, project["Project_ID"], "clear")
        ).status_code == 200
    state = await workspace(data, judge_id)
    response = await client.post(
        f"/api/v1/mentor-review/asm/{judge_id}/complete",
        json={"Context": state["Context"]},
    )
    assert response.status_code == 200, response.text
    admin = (await client.get(f"/api/v1/judges/{judge_id}")).json()
    assert not admin["Conflict_Review_Required"] and admin["Previous_Name"] is None
    # Reviews protect their source records, even when no scores/conflicts exist.
    assert (await client.delete(f"/api/v1/judges/{judge_id}")).status_code == 409
    assert (
        await client.delete(f"/api/v1/projects/{data['projects'][1]['Project_ID']}")
    ).status_code == 409


@pytest.mark.asyncio
async def test_csv_judges_preview_apply_repeat_and_existing_identity_preserved(context):
    data = await prepared(context)
    client = data["client"]
    content = (
        "First_Name,Last_Name,Email,Department\r\n"
        "María,New Judge,maria@example.org,Microbiology\r\n"
    )
    preview = (await upload(client, "judges", content)).json()
    assert not preview["Errors"] and preview["Rows"][0]["Action"] == "create"
    assert len((await client.get("/api/v1/judges/?event_id=asm")).json()) == 3
    response = await upload(client, "judges", content, preview)
    assert response.status_code == 200 and response.json()["Applied"]
    judges = (await client.get("/api/v1/judges/?event_id=asm")).json()
    created = next(j for j in judges if j["First_Name"] == "María")
    assert len(created["Access_Code"]) == 6
    repeated = (await upload(client, "judges", content)).json()
    assert "Possible existing judge" in repeated["Errors"][0]
    assert (await upload(client, "judges", content, repeated)).status_code == 422
    content = csv_file(
        [
            {
                "Judge_ID": created["Judge_ID"],
                "First_Name": "Maria",
                "Last_Name": "New Judge",
                "Email": "maria@example.org",
                "Department": "Biology",
            }
        ]
    )
    preview = (await upload(client, "judges", content)).json()
    assert (await upload(client, "judges", content, preview)).status_code == 200
    updated = (await client.get(f"/api/v1/judges/{created['Judge_ID']}")).json()
    assert (
        updated["Judge_ID"] == created["Judge_ID"]
        and updated["Access_Code"] == created["Access_Code"]
    )
    assert updated["First_Name"] == "Maria" and updated["Conflict_Review_Required"]


@pytest.mark.asyncio
async def test_decision_sheet_import_is_atomic_and_rejects_stale_changes(context):
    data = await prepared(context)
    client, judge_id = data["client"], data["judges"][0]["Judge_ID"]
    template = (
        await client.get(
            f"/api/v1/mentor-review/asm/template/decisions?judge_id={judge_id}"
        )
    ).json()
    rows = list(csv.DictReader(io.StringIO(template["content"])))
    rows[0].update(Decision="conflict", Note="Paul confirmed mentor")
    rows[1].update(Decision="clear", Note="   ")
    content = csv_file(rows)
    preview = (await upload(client, "decisions", content)).json()
    assert preview["Errors"] and len(preview["Rows"]) == 1
    assert (await upload(client, "decisions", content, preview)).status_code == 422
    assert (await client.get("/api/v1/competition/asm/conflicts")).json() == []
    rows[1].update(Decision="needs_input", Note="Ask Paul to resolve a lab name")
    content = csv_file(rows)
    preview = (await upload(client, "decisions", content)).json()
    assert not preview["Errors"]
    response = await upload(client, "decisions", content, preview)
    assert response.status_code == 200, response.text
    state = await workspace(data, judge_id)
    assert [p["Status"] for p in state["Projects"]] == [
        "conflict",
        "needs_input",
        "unreviewed",
    ]
    assert (
        "outdated" in (await upload(client, "decisions", content)).json()["Errors"][0]
    )
    # Roster changes after a preview invalidate the whole apply, including new judges.
    content = "First_Name,Last_Name\nNew,Person\n"
    preview = (await upload(client, "judges", content)).json()
    await client.patch(
        f"/api/v1/projects/{data['projects'][0]['Project_ID']}",
        json={"Advisor_Name": "Changed"},
    )
    assert (await upload(client, "judges", content, preview)).status_code == 409
    assert len((await client.get("/api/v1/judges/?event_id=asm")).json()) == 3


@pytest.mark.asyncio
async def test_review_auth_event_scoping_and_input_validation(context):
    data = await prepared(context)
    client, _, app = context
    judge_id, project_id = (
        data["judges"][0]["Judge_ID"],
        data["projects"][0]["Project_ID"],
    )
    base = f"/api/v1/mentor-review/asm/{judge_id}/{project_id}"
    row = (await workspace(data, judge_id))["Projects"][0]
    for changes in (
        {"Note": "  "},
        {"Decision": "auto"},
        {"Note": "x" * 501},
        {"Judge_ID": "other"},
    ):
        response = await client.put(
            base,
            json={
                "Context": row["Context"],
                "Decision": "clear",
                "Note": "Paul",
                **changes,
            },
        )
        assert response.status_code == 422
    assert (await client.get("/api/v1/mentor-review/missing")).status_code == 404
    assert (
        await client.get("/api/v1/mentor-review/asm?judge_id=missing")
    ).status_code == 404
    assert (
        await client.put(
            f"/api/v1/mentor-review/asm/{judge_id}/missing",
            json={"Context": row["Context"], "Decision": "clear", "Note": "Paul"},
        )
    ).status_code == 404
    override = app.dependency_overrides.pop(get_current_admin)
    try:
        for role in (None, "judge", "voter"):
            headers = (
                {"Authorization": "Bearer " + create_access_token(judge_id, role)}
                if role
                else {}
            )
            assert (
                await client.get("/api/v1/mentor-review/asm", headers=headers)
            ).status_code == 401
            assert (
                await client.put(
                    base,
                    headers=headers,
                    json={
                        "Context": row["Context"],
                        "Decision": "clear",
                        "Note": "Paul",
                    },
                )
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/mentor-review/asm/imports/judges",
                    headers=headers,
                    files={
                        "file": ("judges.csv", "First_Name,Last_Name\nNew,Person\n")
                    },
                )
            ).status_code == 401
    finally:
        app.dependency_overrides[get_current_admin] = override


def test_review_migration_is_repeatable_and_preserves_populated_decisions(
    tmp_path, monkeypatch
):
    database = tmp_path / "mentor.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    engine = sa.create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        Base.metadata.create_all(connection)
        MentorReview.__table__.drop(connection)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.stamp(config, "20261028_judge_profile")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                'INSERT INTO "Mentor_Review" ("Judge_ID", "Project_ID", "Decision", '
                '"Note", "Source_Context", "Reviewed_By", "Reviewed_At") VALUES '
                "('judge', 'poster', 'needs_input', 'Ask Paul', 'context', "
                "'test', CURRENT_TIMESTAMP)"
            )
        )
    with pytest.raises(RuntimeError, match="Archive mentor review"):
        command.downgrade(config, "20261028_judge_profile")
    engine.dispose()
