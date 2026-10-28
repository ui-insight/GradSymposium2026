"""Five-point scoring, legacy limits, repeatable setup and history-safe upgrades."""

import datetime
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from openpyxl import load_workbook
from test_competition import assigned_to, judge_headers, prepared, score_payload
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.config import settings
from app.db.base import Base
from app.db.schema import _ensure_runtime_schema_sync
from app.db.score_scale import ensure_score_range
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.score_override import ScoreOverride
from app.models.user import User
from app.services.asm_rubric import CRITERIA, SCORE_LABELS, configure_asm_rubric

context = poster_context


@pytest.mark.asyncio
async def test_asm_review_help_overrides_results_and_export(context):
    client, sessions, _ = context
    async with sessions() as db:
        db.add(User(User_ID="test-admin", Username="test", Hashed_Password="unused"))
        db.add(CompetitionSettings(Event_ID="asm"))
        rubric = await configure_asm_rubric(db, "asm")
        rubric_id = rubric.Rubric_ID
        criterion_ids = [c.Criterion_ID for c in rubric.criteria]
        await db.commit()
    project = await create(client, Judging_Eligible=True, Award_Groups=[])
    judge = (
        await client.post(
            "/api/v1/judges/",
            json={"Event_ID": "asm", "First_Name": "Test", "Last_Name": "Judge"},
        )
    ).json()
    assert (
        await client.put(
            "/api/v1/competition/asm/settings",
            json={
                "Required_Reviews": 1,
                "Assignment_Only": False,
                "Aggregation": "average",
                "Tie_Policy": "shared",
                "Award_Groups": [],
                "Rules_Confirmed": True,
            },
        )
    ).status_code == 200
    assert (await client.post(f"/api/v1/rubrics/{rubric_id}/lock")).status_code == 200
    assert (await client.post("/api/v1/competition/asm/open")).status_code == 200
    token = (
        await client.post(
            "/api/v1/judge/login", json={"access_code": judge["Access_Code"]}
        )
    ).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    url = f"/api/v1/judge/projects/{project['Project_ID']}"
    detail = (await client.get(url, headers=headers)).json()
    assert detail["rubric"]["Max_Score"] == 20
    assert detail["rubric"]["Score_Labels"] == SCORE_LABELS
    assert [
        (c["Criterion_Name"], c["Description"]) for c in detail["rubric"]["criteria"]
    ] == list(CRITERIA)

    def payload(values):
        return {
            "scores": [
                {"Criterion_ID": criterion_id, "Score_Value": value}
                for criterion_id, value in zip(criterion_ids, values)
            ],
            "feedback": "Clear explanation",
        }

    for values in ([5, 5, 5, 5], [0, 1, 2, 3], [4, 5, 4, 5]):
        response = await client.post(
            url + "/scores", headers=headers, json=payload(values)
        )
        assert response.status_code == 200, response.text
        result = (await client.get("/api/v1/results/?event_id=asm")).json()[0]
        assert result["Judge_Count"] == 1
        assert result["Total_Score"] == result["Average_Score"] == sum(values)
        assert result["Meets_Review_Target"]
        workbook = load_workbook(
            io.BytesIO(
                (await client.get("/api/v1/results/export?event_id=asm")).content
            )
        )
        assert workbook["Poster Rankings"]["G2"].value == sum(values)
        assert workbook["Poster Rankings"]["H2"].value == sum(values)
    for values in (
        [6, 5, 5, 5],
        [-1, 5, 5, 5],
        [True, 5, 5, 5],
        [2.5, 5, 5, 5],
        [5, 5, 5],
    ):
        assert (
            await client.post(url + "/scores", headers=headers, json=payload(values))
        ).status_code == 422
    assert (await client.get("/api/v1/results/?event_id=asm")).json()[0][
        "Total_Score"
    ] == 18
    review = (await client.get(f"/api/v1/scores/review/{project['Project_ID']}")).json()
    criterion = review["submissions"][0]["criteria"][0]
    override = await client.patch(
        f"/api/v1/scores/{criterion['Score_ID']}", json={"Score_Value": 5}
    )
    assert override.status_code == 200, override.text
    assert (await client.get("/api/v1/results/?event_id=asm")).json()[0][
        "Total_Score"
    ] == 19
    async with sessions() as db:
        audit = (await db.scalars(sa.select(ScoreOverride))).one()
        assert (audit.Old_Score_Value, audit.New_Score_Value) == (4, 5)
        assert (await configure_asm_rubric(db, "asm")).Rubric_ID == rubric_id
        await db.commit()
    assert (
        await client.patch(
            f"/api/v1/rubrics/criteria/{criterion_ids[0]}", json={"Max_Score": 3}
        )
    ).status_code == 409


@pytest.mark.asyncio
async def test_legacy_three_point_limits_still_apply(context):
    data = await prepared(context)
    project = data["projects"][0]
    headers = await judge_headers(data, assigned_to(data, project)[0])
    url = f"/api/v1/judge/projects/{project['Project_ID']}"
    detail = (await data["client"].get(url, headers=headers)).json()
    assert detail["rubric"]["Score_Labels"] is None
    assert all(c["Max_Score"] == 3 for c in detail["rubric"]["criteria"])
    for value in (4, 5):
        response = await data["client"].post(
            url + "/scores", headers=headers, json=score_payload(data, value)
        )
        assert response.status_code == 422
    assert (
        await data["client"].post(
            url + "/scores", headers=headers, json=score_payload(data)
        )
    ).status_code == 200
    score = (await data["client"].get("/api/v1/scores/?event_id=asm")).json()[0]
    assert (
        await data["client"].patch(
            f"/api/v1/scores/{score['Score_ID']}", json={"Score_Value": 4}
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_setup_preserves_drafts_locks_and_other_events(context):
    _, sessions, _ = context
    async with sessions() as db:
        db.add(CompetitionSettings(Event_ID="asm"))
        db.add(
            Event(
                Event_ID="gpsa",
                Event_Name="Historical GPSA",
                Event_Date=datetime.date(2026, 3, 13),
            )
        )
        historical = Rubric(
            Event_ID="gpsa", Rubric_Name="Original", Category="Poster", Max_Score=3
        )
        historical.criteria = [RubricCriterion(Criterion_Name="Original")]
        db.add(historical)
        draft = Rubric(
            Event_ID="asm", Rubric_Name="Pending", Category="Poster", Max_Score=0
        )
        db.add(draft)
        await db.flush()
        rubric = await configure_asm_rubric(db, "asm")
        assert rubric.Rubric_ID == draft.Rubric_ID
        ids = [c.Criterion_ID for c in rubric.criteria]
        await db.commit()
        assert [
            c.Criterion_ID for c in (await configure_asm_rubric(db, "asm")).criteria
        ] == ids
        assert not rubric.Is_Locked
        assert not (await db.get(CompetitionSettings, "asm")).Judging_Open
        assert historical.Max_Score == 3 and historical.Score_Labels is None
        rubric.Is_Locked = True
        await db.commit()
        assert (await configure_asm_rubric(db, "asm")).Is_Locked
        rubric.criteria[0].Description = "Organizer correction"
        await db.commit()
        with pytest.raises(RuntimeError, match="nothing was replaced"):
            await configure_asm_rubric(db, "asm")
        assert rubric.criteria[0].Description == "Organizer correction"


@pytest.mark.parametrize("runtime", [False, True])
def test_populated_upgrade_preserves_scores_and_override_references(
    tmp_path, monkeypatch, runtime
):
    database = tmp_path / "old-scores.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    engine = sa.create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        Base.metadata.create_all(connection)
        ensure_score_range(connection, maximum=3)
        connection.exec_driver_sql('ALTER TABLE "Rubric" DROP COLUMN "Score_Labels"')
    # SQL inserts intentionally model the old schema without the new JSON field.
    with engine.begin() as connection:
        for statement in (
            """INSERT INTO "Event" ("Event_ID", "Event_Name", "Event_Date")
               VALUES ('old', 'GPSA', '2026-03-13')""",
            """INSERT INTO "Rubric" ("Rubric_ID", "Event_ID", "Rubric_Name",
               "Category", "Max_Score") VALUES ('r', 'old', 'Original', 'Poster', 3)""",
            """INSERT INTO "Rubric_Criterion" ("Criterion_ID", "Rubric_ID",
               "Criterion_Name") VALUES (1, 'r', 'Original')""",
            """INSERT INTO "Judge" ("Judge_ID", "Event_ID", "First_Name",
               "Last_Name", "Access_Code") VALUES ('j', 'old', 'A', 'B', 'ABCDEF')""",
            """INSERT INTO "Project" ("Project_ID", "Event_ID", "Project_Number",
               "Project_Title", "Presenter_First_Name", "Presenter_Last_Name",
               "Category") VALUES ('p', 'old', 'P-001', 'Title', 'A', 'B', 'Poster')""",
            """INSERT INTO "User" ("User_ID", "Username", "Hashed_Password")
               VALUES ('u', 'admin', 'unused')""",
            """INSERT INTO "Score" ("Score_ID", "Judge_ID", "Project_ID",
               "Criterion_ID", "Score_Value") VALUES (42, 'j', 'p', 1, 3)""",
            """INSERT INTO "Score_Override" ("Score_ID", "Admin_User_ID",
               "Old_Score_Value", "New_Score_Value") VALUES (42, 'u', 2, 3)""",
        ):
            connection.exec_driver_sql(statement)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.stamp(config, "20261027_competition")
    if runtime:
        with engine.begin() as connection:
            _ensure_runtime_schema_sync(connection)
            _ensure_runtime_schema_sync(connection)
    else:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
    with engine.begin() as connection:
        assert connection.exec_driver_sql(
            'SELECT "Score_ID", "Score_Value" FROM "Score"'
        ).one() == (42, 3)
        assert connection.exec_driver_sql(
            'SELECT "Score_ID", "Old_Score_Value", "New_Score_Value" '
            'FROM "Score_Override"'
        ).one() == (42, 2, 3)
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        connection.exec_driver_sql('UPDATE "Score" SET "Score_Value" = 5')
    if not runtime:
        with pytest.raises(RuntimeError, match="five-point"):
            command.downgrade(config, "20261027_competition")
    with engine.connect() as connection:
        assert connection.scalar(sa.text('SELECT "Score_Value" FROM "Score"')) == 5
    engine.dispose()
