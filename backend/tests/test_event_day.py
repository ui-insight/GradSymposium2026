"""Event-day replacement and separate talk voting through real HTTP routes."""

import datetime

import pytest
from sqlalchemy import select
from test_competition import assigned_to, judge_headers, prepared, score_payload
from test_poster_directory import context as poster_context

from app.db.schema import ensure_runtime_schema
from app.models.talk import TalkBallot, TalkCandidate
from app.models.voting_round import VotingRound

context = poster_context


@pytest.mark.asyncio
async def test_atomic_reported_conflict(context):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    outgoing = assigned_to(data, project)[0]
    incoming = next(
        j["Judge_ID"]
        for j in data["judges"]
        if j["Judge_ID"] not in assigned_to(data, project)
    )
    assignment = next(
        a
        for a in data["assignments"]
        if a["Judge_ID"] == outgoing and a["Project_ID"] == project["Project_ID"]
    )
    headers = await judge_headers(data, outgoing)
    response = await client.post(
        f"/api/v1/judge/projects/{project['Project_ID']}/scores",
        headers=headers,
        json=score_payload(data),
    )
    assert response.status_code == 200
    payload = {
        "Assignment_ID": assignment["Assignment_ID"],
        "Judge_ID": outgoing,
        "Project_ID": project["Project_ID"],
        "Replacement_Judge_ID": outgoing,
        "Reason": "Mentor reported in person",
    }
    assert (
        await client.post("/api/v1/assignments/report-conflict", json=payload)
    ).status_code == 422
    assert len((await client.get("/api/v1/assignments/?event_id=asm")).json()) == 6
    payload["Replacement_Judge_ID"] = incoming
    response = await client.post("/api/v1/assignments/report-conflict", json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {"assigned": 2, "completed_reviews": 0, "target": 2}
    assert (
        await client.post("/api/v1/assignments/report-conflict", json=payload)
    ).status_code == 409
    response = await client.post(
        f"/api/v1/judge/projects/{project['Project_ID']}/scores",
        headers=headers,
        json=score_payload(data),
    )
    assert response.status_code == 403
    await client.post(
        "/api/v1/assignments/auto", json={"Event_ID": "asm", "Judges_Per_Project": 3}
    )
    assignments = (await client.get("/api/v1/assignments/?event_id=asm")).json()
    assert not any(
        a["Judge_ID"] == outgoing and a["Project_ID"] == project["Project_ID"]
        for a in assignments
    )
    current = next(a for a in assignments if a["Project_ID"] == project["Project_ID"])
    response = await client.post(
        "/api/v1/assignments/report-conflict",
        json={
            "Assignment_ID": current["Assignment_ID"],
            "Judge_ID": current["Judge_ID"],
            "Project_ID": current["Project_ID"],
            "Reason": "Reported conflict, no replacement",
        },
    )
    assert response.status_code == 200
    assert response.json()["assigned"] == 1


@pytest.mark.asyncio
async def test_separate_talk_ballots_and_trainee_boundary(context):
    client, sessions, app = context
    response = await client.post("/api/v1/voting/admin/prepare-talks/asm")
    assert response.status_code == 201, response.text
    assert (
        await client.post("/api/v1/voting/admin/prepare-talks/asm")
    ).status_code == 409
    rounds = (await client.get("/api/v1/voting/admin/rounds?event_id=asm")).json()
    assert len(rounds) == 2
    pools = [
        (await client.get(f"/api/v1/voting/admin/rounds/{r['Round_ID']}/talks")).json()
        for r in rounds
    ]
    assert sorted(map(len, pools)) == [6, 8]
    assert any(
        c["Presenter_Display_Name"] == "Andrea Gómez" for pool in pools for c in pool
    )
    issued = await client.post(
        "/api/v1/voting/admin/voters",
        json={"Event_ID": "asm", "Registration_Reference": "trainee-1"},
    )
    assert issued.status_code == 201, issued.text
    voter = issued.json()["voter"]
    code = issued.json()["access_code"]
    login = await client.post("/api/v1/voting/login", json={"access_code": code})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    r = rounds[0]
    path = f"/api/v1/voting/rounds/{r['Round_ID']}"
    assert (await client.get(path + "/posters", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/voting/me", headers=headers)).json()[
        "rounds"
    ] == []
    access = {
        "Is_Trainee": True,
        "Talk_Affiliation_Confirmed": True,
        "Presenter_Talk_IDs": [],
    }
    assert (
        await client.put(
            f"/api/v1/voting/admin/voters/{voter['Voter_ID']}/talk-access", json=access
        )
    ).status_code == 200
    instant = datetime.datetime.now(datetime.timezone.utc)
    for round_ in rounds:
        response = await client.put(
            f"/api/v1/voting/admin/rounds/{round_['Round_ID']}",
            json={
                **round_,
                "Min_Choices": 1,
                "Max_Choices": 1,
                "Ranked": False,
                "Allow_Self_Votes": False,
                "Allow_Edits": False,
                "Rules_Confirmed": True,
                "Opens_At": (instant - datetime.timedelta(hours=1)).isoformat(),
                "Closes_At": (instant + datetime.timedelta(hours=1)).isoformat(),
            },
        )
        assert response.status_code == 200, response.text
        response = await client.post(
            f"/api/v1/voting/admin/rounds/{round_['Round_ID']}/open"
        )
        assert response.status_code == 200, response.text
    candidates = (await client.get(path + "/posters", headers=headers)).json()
    assert len(candidates) == len(pools[0])
    assert all(c["Project_Number"] == "" for c in candidates)
    assert (
        await client.post(
            path + "/ballot",
            headers=headers,
            json={"Project_IDs": [pools[1][0]["Candidate_ID"]]},
        )
    ).status_code == 422
    candidate = candidates[0]["Project_ID"]
    access["Presenter_Talk_IDs"] = [candidate]
    await client.put(
        f"/api/v1/voting/admin/voters/{voter['Voter_ID']}/talk-access", json=access
    )
    assert (
        await client.post(
            path + "/ballot", headers=headers, json={"Project_IDs": [candidate]}
        )
    ).status_code == 422
    access["Presenter_Talk_IDs"] = []
    await client.put(
        f"/api/v1/voting/admin/voters/{voter['Voter_ID']}/talk-access", json=access
    )
    payload = {"Project_IDs": [candidate]}
    response = await client.post(path + "/ballot", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert (
        await client.post(path + "/ballot", headers=headers, json=payload)
    ).status_code == 200
    assert (
        await client.post(
            path + "/ballot",
            headers=headers,
            json={"Project_IDs": [candidates[1]["Project_ID"]]},
        )
    ).status_code == 409
    assert (await client.get(path + "/ballot", headers=headers)).json()[
        "Project_IDs"
    ] == [candidate]
    otherpath = f"/api/v1/voting/rounds/{rounds[1]['Round_ID']}"
    assert not (await client.get(otherpath + "/ballot", headers=headers)).json()[
        "saved"
    ]
    summarypath = f"/api/v1/voting/admin/rounds/{r['Round_ID']}"
    assert (await client.get(summarypath + "/export")).status_code == 409
    await client.post(summarypath + "/close")
    summary = (await client.get(summarypath + "/summary")).json()
    assert summary["Ballots_Submitted"] == 1
    assert sum(c["Votes"] for c in summary["tally"]) == 1
    assert summary["tally"][0]["Votes"] == 1
    assert (await client.get(summarypath + "/export")).status_code == 200
    withdrawn = next(c for c in pools[0] if c["Candidate_ID"] == candidate)
    response = await client.put(
        summarypath + f"/talks/{candidate}", json={**withdrawn, "Is_Active": False}
    )
    assert response.status_code == 200
    summary = (await client.get(summarypath + "/summary")).json()
    assert sum(c["Votes"] for c in summary["tally"]) == 0
    assert summary["Ballots_Submitted"] == 1
    async with sessions() as db:
        assert len(list(await db.scalars(select(TalkBallot)))) == 1
        assert len(list(await db.scalars(select(TalkCandidate)))) == 14
        async with db.bind.begin() as conn:
            await ensure_runtime_schema(conn)
            await ensure_runtime_schema(conn)


@pytest.mark.asyncio
async def test_upgrade_preserves_existing_round_and_voter(context):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    from app.models.voter import Voter

    client, sessions, _ = context
    issued = await client.post(
        "/api/v1/voting/admin/voters",
        json={"Event_ID": "asm", "Registration_Reference": "existing-attendee"},
    )
    voter_id = issued.json()["voter"]["Voter_ID"]
    round_ = (
        await client.post(
            "/api/v1/voting/admin/rounds",
            json={"Event_ID": "asm", "Round_Name": "Original poster ballot"},
        )
    ).json()
    spec = importlib.util.spec_from_file_location(
        "talk_upgrade",
        Path(__file__).parents[1] / "migrations/versions/20261030_talk_voting.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with sessions() as db:
        async with db.bind.begin() as connection:

            def upgrade_old(conn):
                TalkBallot.__table__.drop(conn)
                TalkCandidate.__table__.drop(conn)
                for table, columns in [
                    ("Voting_Round", ["Candidate_Type", "Trainees_Only"]),
                    (
                        "Voter",
                        [
                            "Is_Trainee",
                            "Talk_Affiliation_Confirmed",
                            "Presenter_Talk_IDs",
                        ],
                    ),
                ]:
                    for column in columns:
                        conn.execute(
                            text(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
                        )
                with Operations.context(MigrationContext.configure(conn)):
                    migration.upgrade()
                    migration.upgrade()

            await connection.run_sync(upgrade_old)
        existing = await db.get(Voter, voter_id)
        assert not existing.Is_Trainee
        assert existing.Presenter_Talk_IDs == []
        original = await db.get(VotingRound, round_["Round_ID"])
        assert original.Candidate_Type == "poster"
        assert not original.Trainees_Only
    response = await client.post(
        "/api/v1/voting/login", json={"access_code": issued.json()["access_code"]}
    )
    assert response.status_code == 200
