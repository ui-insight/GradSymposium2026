"""Exercise competition boundaries through real HTTP routes and isolated storage."""

import asyncio
import datetime

import pytest
from sqlalchemy import func, select
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.api.deps import get_current_admin
from app.models.ballot import Ballot
from app.models.ballot_selection import BallotSelection
from app.models.score import Score
from app.models.voter import Voter
from app.models.voting_round import VotingRound

context = poster_context


async def prepared(context):
    client, sessions, app = context
    rubric_response = await client.post(
        "/api/v1/rubrics/",
        json={
            "Event_ID": "asm",
            "Category": "Poster",
            "Rubric_Name": "Example test rubric",
        },
    )
    assert rubric_response.status_code == 201, rubric_response.text
    rubric = rubric_response.json()
    criteria = []
    for name in ("Research", "Communication"):
        response = await client.post(
            f"/api/v1/rubrics/{rubric['Rubric_ID']}/criteria",
            json={"Criterion_Name": name, "Min_Score": 1, "Max_Score": 3},
        )
        assert response.status_code == 201, response.text
        criteria.append(response.json())
    assert (
        await client.post(f"/api/v1/rubrics/{rubric['Rubric_ID']}/lock")
    ).status_code == 200
    projects = [
        await create(
            client,
            Project_Title=f"Test presentation {i}",
            Judging_Eligible=True,
            Voting_Eligible=True,
            Award_Groups=[],
        )
        for i in range(3)
    ]
    judges = []
    for i in range(3):
        response = await client.post(
            "/api/v1/judges/",
            json={"Event_ID": "asm", "First_Name": "Judge", "Last_Name": str(i)},
        )
        assert response.status_code == 201, response.text
        judges.append(response.json())
    response = await client.put(
        "/api/v1/competition/asm/settings",
        json={
            "Required_Reviews": 2,
            "Assignment_Only": True,
            "Aggregation": "average",
            "Tie_Policy": "shared",
            "Award_Groups": [],
            "Rules_Confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    response = await client.post("/api/v1/assignments/auto", json={"Event_ID": "asm"})
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 6
    assert response.json()["shortages"] == []
    response = await client.post("/api/v1/competition/asm/open")
    assert response.status_code == 200, response.text
    assignments = (await client.get("/api/v1/assignments/?event_id=asm")).json()
    return {
        "client": client,
        "sessions": sessions,
        "app": app,
        "rubric": rubric,
        "criteria": criteria,
        "projects": projects,
        "judges": judges,
        "assignments": assignments,
    }


def score_payload(data, value=3):
    return {
        "scores": [
            {"Criterion_ID": criterion["Criterion_ID"], "Score_Value": value}
            for criterion in data["criteria"]
        ],
        "feedback": "Test feedback",
    }


async def judge_headers(data, judge_id):
    judge = next(j for j in data["judges"] if j["Judge_ID"] == judge_id)
    response = await data["client"].post(
        "/api/v1/judge/login", json={"access_code": judge["Access_Code"]}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def assigned_to(data, project):
    return [
        a["Judge_ID"]
        for a in data["assignments"]
        if a["Project_ID"] == project["Project_ID"]
    ]


@pytest.mark.asyncio
async def test_score_validation_is_atomic_and_checks_complete_rubric(context):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    headers = await judge_headers(data, assigned_to(data, project)[0])
    url = f"/api/v1/judge/projects/{project['Project_ID']}/scores"
    valid = score_payload(data)
    for scores in (
        [],
        valid["scores"][:1],
        [valid["scores"][0]] * 2,
        [{"Criterion_ID": 999999, "Score_Value": 3}, valid["scores"][0]],
        [
            {"Criterion_ID": c["Criterion_ID"], "Score_Value": 0}
            for c in data["criteria"]
        ],
        [
            {"Criterion_ID": c["Criterion_ID"], "Score_Value": True}
            for c in data["criteria"]
        ],
    ):
        response = await client.post(url, headers=headers, json={"scores": scores})
        assert response.status_code == 422, response.text
    async with data["sessions"]() as db:
        assert await db.scalar(select(func.count()).select_from(Score)) == 0
    spare = next(
        j for j in data["judges"] if j["Judge_ID"] not in assigned_to(data, project)
    )
    response = await client.post(
        url, headers=await judge_headers(data, spare["Judge_ID"]), json=valid
    )
    assert response.status_code == 403, response.text
    responses = await asyncio.gather(
        *(client.post(url, headers=headers, json=valid) for _ in range(3))
    )
    assert all(response.status_code == 200 for response in responses), [
        r.text for r in responses
    ]
    async with data["sessions"]() as db:
        assert await db.scalar(select(func.count()).select_from(Score)) == 2
    assert (
        await client.post(f"/api/v1/rubrics/{data['rubric']['Rubric_ID']}/unlock")
    ).status_code == 409
    assert (await client.post("/api/v1/competition/asm/close")).status_code == 200
    assert (await client.post(url, headers=headers, json=valid)).status_code == 409


@pytest.mark.asyncio
async def test_coverage_counts_complete_reviews_and_review_target(context):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    assigned = assigned_to(data, project)
    async with data["sessions"]() as db:
        db.add(
            Score(
                Judge_ID=assigned[0],
                Project_ID=project["Project_ID"],
                Criterion_ID=data["criteria"][0]["Criterion_ID"],
                Score_Value=2,
            )
        )
        await db.commit()
    summary = (await client.get("/api/v1/results/summary?event_id=asm")).json()
    assert summary["Total_Scores_Submitted"] == 0
    assert (await client.get("/api/v1/results/?event_id=asm")).json() == []
    for index, judge_id in enumerate(assigned):
        response = await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=await judge_headers(data, judge_id),
            json=score_payload(data),
        )
        assert response.status_code == 200, response.text
        summary = (await client.get("/api/v1/results/summary?event_id=asm")).json()
        assert summary["Total_Scores_Submitted"] == index + 1
        assert summary["Projects_At_Target"] == index
    state = (await client.get("/api/v1/competition/asm")).json()
    row = next(p for p in state["coverage"] if p["Project_ID"] == project["Project_ID"])
    assert (row["Complete_Reviews"], row["Missing_Reviews"]) == (2, 0)
    result = (await client.get("/api/v1/results/?event_id=asm")).json()[0]
    assert result["Meets_Review_Target"]
    assert result["Provisional"]  # Other eligible posters still lack reviews.
    assert result["Average_Score"] == 6


@pytest.mark.asyncio
async def test_recorded_conflict_removes_assignment_and_excludes_retained_scores(
    context,
):
    data = await prepared(context)
    client, project = data["client"], data["projects"][0]
    judge_id = assigned_to(data, project)[0]
    headers = await judge_headers(data, judge_id)
    response = await client.post(
        f"/api/v1/judge/projects/{project['Project_ID']}/scores",
        headers=headers,
        json=score_payload(data),
    )
    assert response.status_code == 200
    response = await client.post(
        "/api/v1/competition/asm/conflicts",
        json={
            "Judge_ID": judge_id,
            "Project_ID": project["Project_ID"],
            "Reason": "Explicit test conflict",
        },
    )
    assert response.status_code == 201, response.text
    assert (await client.get("/api/v1/results/?event_id=asm")).json() == []
    assert (
        await client.post(
            "/api/v1/assignments/",
            json={"Judge_ID": judge_id, "Project_ID": project["Project_ID"]},
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/judge/projects/{project['Project_ID']}/scores",
            headers=headers,
            json=score_payload(data),
        )
    ).status_code == 403
    async with data["sessions"]() as db:
        assert await db.scalar(select(func.count()).select_from(Score)) == 2


async def voting_setup(context, **changes):
    data = await prepared(context)
    moment = datetime.datetime.now(datetime.timezone.utc)
    body = {
        "Event_ID": "asm",
        "Round_Name": "Test ballot rules",
        "Min_Choices": 1,
        "Max_Choices": 2,
        "Ranked": False,
        "Allow_Self_Votes": False,
        "Allow_Edits": False,
        "Opens_At": (moment - datetime.timedelta(minutes=5)).isoformat(),
        "Closes_At": (moment + datetime.timedelta(hours=1)).isoformat(),
        "Rules_Confirmed": True,
        **changes,
    }
    response = await data["client"].post("/api/v1/voting/admin/rounds", json=body)
    assert response.status_code == 201, response.text
    round_ = response.json()
    response = await data["client"].post(
        f"/api/v1/voting/admin/rounds/{round_['Round_ID']}/open"
    )
    assert response.status_code == 200, response.text
    data["round"] = round_
    data["round_body"] = body
    return data


async def voter_credentials(data, **changes):
    client = data["client"]
    response = await client.post(
        "/api/v1/voting/admin/voters",
        json={
            "Event_ID": "asm",
            "Registration_Reference": "test-attendee",
            "Affiliation_Confirmed": True,
            "Presenter_Project_IDs": [],
            **changes,
        },
    )
    assert response.status_code == 201, response.text
    issued = response.json()
    login = await client.post(
        "/api/v1/voting/login", json={"access_code": issued["access_code"]}
    )
    assert login.status_code == 200, login.text
    return issued, {"Authorization": "Bearer " + login.json()["access_token"]}


@pytest.mark.asyncio
async def test_ballot_retry_concurrency_role_isolation_and_credential_replacement(
    context,
):
    data = await voting_setup(context)
    client = data["client"]
    issued, headers = await voter_credentials(data)
    voter_id = issued["voter"]["Voter_ID"]
    url = f"/api/v1/voting/rounds/{data['round']['Round_ID']}/ballot"
    ids = [p["Project_ID"] for p in data["projects"][:2]]
    responses = await asyncio.gather(
        *(
            client.post(url, headers=headers, json={"Project_IDs": ids})
            for _ in range(4)
        )
    )
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    async with data["sessions"]() as db:
        assert await db.scalar(select(func.count()).select_from(Ballot)) == 1
        assert await db.scalar(select(func.count()).select_from(BallotSelection)) == 2
        voter = await db.get(Voter, voter_id)
        assert voter.Code_Hash != issued["access_code"]
    assert (
        await client.post(
            url,
            headers=headers,
            json={"Project_IDs": [data["projects"][2]["Project_ID"]]},
        )
    ).status_code == 409
    status = (
        await client.get(
            f"/api/v1/voting/admin/rounds/{data['round']['Round_ID']}/summary"
        )
    ).json()
    assert status["Ballots_Submitted"] == 1
    assert status["tally"] == []
    assert (
        await client.get(
            f"/api/v1/voting/admin/rounds/{data['round']['Round_ID']}/export"
        )
    ).status_code == 409
    app = data["app"]
    override = app.dependency_overrides.pop(get_current_admin)
    assert (
        await client.get("/api/v1/projects/?event_id=asm", headers=headers)
    ).status_code == 401
    assert (
        await client.get("/api/v1/judge/projects", headers=headers)
    ).status_code == 401
    app.dependency_overrides[get_current_admin] = override
    replacement = await client.post(
        f"/api/v1/voting/admin/voters/{voter_id}/replace-code"
    )
    assert replacement.status_code == 200, replacement.text
    assert (await client.get(url, headers=headers)).status_code == 401
    assert (
        await client.post(
            "/api/v1/voting/login", json={"access_code": issued["access_code"]}
        )
    ).status_code == 401
    login = await client.post(
        "/api/v1/voting/login", json={"access_code": replacement.json()["access_code"]}
    )
    renewed = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert (await client.get(url, headers=renewed)).json()["Project_IDs"] == ids
    assert (
        await client.post(url, headers=renewed, json={"Project_IDs": ids})
    ).status_code == 200
    assert (
        await client.post(f"/api/v1/voting/admin/voters/{voter_id}/revoke")
    ).status_code == 204
    assert (await client.get(url, headers=renewed)).status_code == 401


@pytest.mark.asyncio
async def test_voting_selection_validation_closing_and_withdrawal(context):
    data = await voting_setup(context)
    client = data["client"]
    own = data["projects"][0]["Project_ID"]
    issued, headers = await voter_credentials(data, Presenter_Project_IDs=[own])
    round_id = data["round"]["Round_ID"]
    url = f"/api/v1/voting/rounds/{round_id}/ballot"
    for ids in (
        [own],
        [own, own],
        ["foreign-project"],
        [p["Project_ID"] for p in data["projects"]],
    ):
        assert (
            await client.post(url, headers=headers, json={"Project_IDs": ids})
        ).status_code == 422
    selected = data["projects"][1]["Project_ID"]
    response = await client.post(url, headers=headers, json={"Project_IDs": [selected]})
    assert response.status_code == 200, response.text
    await client.post(f"/api/v1/projects/{selected}/withdraw")
    assert (
        await client.post(f"/api/v1/voting/admin/rounds/{round_id}/close")
    ).status_code == 200
    assert (
        await client.post(
            url,
            headers=headers,
            json={"Project_IDs": [data["projects"][2]["Project_ID"]]},
        )
    ).status_code == 409
    status = (
        await client.get(f"/api/v1/voting/admin/rounds/{round_id}/summary")
    ).json()
    assert status["Tallies_Available"]
    assert sum(row["Votes"] for row in status["tally"]) == 0
    assert (await client.get(url, headers=headers)).json()["Project_IDs"] == [selected]
    exported = await client.get(f"/api/v1/voting/admin/rounds/{round_id}/export")
    assert exported.status_code == 200
    assert "test-attendee" not in exported.text
    async with data["sessions"]() as db:
        assert await db.scalar(select(func.count()).select_from(BallotSelection)) == 1


@pytest.mark.asyncio
async def test_ranked_edits_and_time_window_are_server_enforced(context):
    data = await voting_setup(context, Ranked=True, Allow_Edits=True)
    client = data["client"]
    _, headers = await voter_credentials(data)
    round_id = data["round"]["Round_ID"]
    url = f"/api/v1/voting/rounds/{round_id}/ballot"
    ids = [p["Project_ID"] for p in data["projects"][:2]]
    assert (
        await client.post(url, headers=headers, json={"Project_IDs": ids})
    ).status_code == 200
    assert (
        await client.post(url, headers=headers, json={"Project_IDs": ids[::-1]})
    ).status_code == 200
    assert (await client.get(url, headers=headers)).json()["Project_IDs"] == ids[::-1]
    async with data["sessions"]() as db:
        selections = list(
            await db.scalars(select(BallotSelection).order_by(BallotSelection.Rank))
        )
        assert [selection.Project_ID for selection in selections] == ids[::-1]
        round_ = await db.get(VotingRound, round_id)
        round_.Closes_At = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(seconds=1)
        await db.commit()
    assert (
        await client.post(url, headers=headers, json={"Project_IDs": ids})
    ).status_code == 409
    assert (
        await client.put(
            f"/api/v1/voting/admin/rounds/{round_id}",
            json={
                key: value
                for key, value in data["round_body"].items()
                if key != "Event_ID"
            },
        )
    ).status_code == 409
    status = (
        await client.get(f"/api/v1/voting/admin/rounds/{round_id}/summary")
    ).json()
    assert status["Tallies_Available"]
    assert sum(row["Votes"] for row in status["tally"]) == 2
    assert {rank for row in status["tally"] for rank in row["Rank_Counts"]} == {
        "1",
        "2",
    }


@pytest.mark.asyncio
async def test_unconfirmed_rules_cannot_open_and_bulk_entitlements_are_atomic(context):
    client, sessions, _ = context
    assert (await client.post("/api/v1/competition/asm/open")).status_code == 409
    response = await client.post(
        "/api/v1/voting/admin/rounds",
        json={"Event_ID": "asm", "Round_Name": "Rules pending"},
    )
    assert response.status_code == 201, response.text
    assert (
        await client.post(
            f"/api/v1/voting/admin/rounds/{response.json()['Round_ID']}/open"
        )
    ).status_code == 409
    assert (
        await client.post(
            "/api/v1/voting/admin/voters/bulk",
            json={"Event_ID": "asm", "Registration_References": ["Same", "same"]},
        )
    ).status_code == 422
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Voter)) == 0
    response = await client.post(
        "/api/v1/voting/admin/voters/bulk",
        json={"Event_ID": "asm", "Registration_References": ["one", "two"]},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()) == 2
    assert (
        await client.post(
            "/api/v1/voting/admin/voters/bulk",
            json={"Event_ID": "asm", "Registration_References": ["three", "one"]},
        )
    ).status_code == 409
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Voter)) == 2


@pytest.mark.asyncio
async def test_event_isolation_and_atomic_assignment_validation(context):
    from app.models.event import Event

    data = await voting_setup(context)
    client = data["client"]
    async with data["sessions"]() as db:
        db.add(
            Event(
                Event_ID="other",
                Event_Name="Other event",
                Event_Date=datetime.date(2026, 11, 1),
                Is_Active=False,
            )
        )
        await db.commit()
    foreign = await create(
        client, Event_ID="other", Judging_Eligible=True, Voting_Eligible=True
    )
    judge = data["judges"][0]
    headers = await judge_headers(data, judge["Judge_ID"])
    assert (
        await client.get(
            f"/api/v1/judge/projects/{foreign['Project_ID']}", headers=headers
        )
    ).status_code == 404
    before = (await client.get("/api/v1/assignments/?event_id=asm")).json()
    assert (
        await client.delete("/api/v1/assignments/clear?event_id=asm")
    ).status_code == 204
    response = await client.post(
        "/api/v1/assignments/bulk",
        json={
            "assignments": [
                {
                    "Judge_ID": judge["Judge_ID"],
                    "Project_ID": data["projects"][0]["Project_ID"],
                },
                {"Judge_ID": judge["Judge_ID"], "Project_ID": foreign["Project_ID"]},
            ]
        },
    )
    assert response.status_code == 422, response.text
    assert (await client.get("/api/v1/assignments/?event_id=asm")).json() == []
    assert len(before) == 6
    other_round = (
        await client.post(
            "/api/v1/voting/admin/rounds",
            json={"Event_ID": "other", "Round_Name": "Other round"},
        )
    ).json()
    _, voter = await voter_credentials(data)
    for path in ("ballot", "posters"):
        assert (
            await client.get(
                f"/api/v1/voting/rounds/{other_round['Round_ID']}/{path}", headers=voter
            )
        ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/voting/rounds/{other_round['Round_ID']}/ballot",
            headers=voter,
            json={"Project_IDs": [foreign["Project_ID"]]},
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/voting/rounds/{data['round']['Round_ID']}/ballot",
            headers=voter,
            json={"Project_IDs": [foreign["Project_ID"]]},
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/judges/bulk",
            json={
                "Event_ID": "asm",
                "judges": [
                    {"Event_ID": "other", "First_Name": "Wrong", "Last_Name": "Event"}
                ],
            },
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_award_groups_shared_ties_and_rule_freezing(context):
    data = await prepared(context)
    client = data["client"]
    assert (await client.post("/api/v1/competition/asm/close")).status_code == 200
    rules = {
        "Required_Reviews": 2,
        "Assignment_Only": True,
        "Aggregation": "average",
        "Tie_Policy": "shared",
        "Award_Groups": ["Example award"],
        "Rules_Confirmed": True,
    }
    assert (
        await client.put("/api/v1/competition/asm/settings", json=rules)
    ).status_code == 200
    for project in data["projects"]:
        assert (
            await client.patch(
                f"/api/v1/projects/{project['Project_ID']}",
                json={"Award_Groups": ["Example award"]},
            )
        ).status_code == 200
    assert (await client.post("/api/v1/competition/asm/open")).status_code == 200
    assert (
        await client.patch(
            f"/api/v1/projects/{data['projects'][0]['Project_ID']}",
            json={"Judging_Eligible": False},
        )
    ).status_code == 409
    for index, project in enumerate(data["projects"]):
        for judge_id in assigned_to(data, project):
            response = await client.post(
                f"/api/v1/judge/projects/{project['Project_ID']}/scores",
                headers=await judge_headers(data, judge_id),
                json=score_payload(data, value=3 if index < 2 else 2),
            )
            assert response.status_code == 200, response.text
    await client.post("/api/v1/competition/asm/close")
    overview = (await client.get("/api/v1/results/?event_id=asm")).json()
    assert all(row["Rank"] == 0 and row["Provisional"] for row in overview)
    ranked = (
        await client.get("/api/v1/results/?event_id=asm&award_group=Example%20award")
    ).json()
    assert [row["Rank"] for row in ranked] == [1, 1, 3]
    assert [row["Tied"] for row in ranked] == [True, True, False]
    assert all(not row["Provisional"] for row in ranked)
    await client.post("/api/v1/competition/asm/close")
    assert (
        await client.put(
            "/api/v1/competition/asm/settings", json={**rules, "Aggregation": "total"}
        )
    ).status_code == 409
    assert (
        await client.post(f"/api/v1/rubrics/{data['rubric']['Rubric_ID']}/unlock")
    ).status_code == 409
    # Losing a review makes that presentation provisional; history is retained.
    project = data["projects"][0]
    assert (
        await client.delete(
            f"/api/v1/scores/submissions/{project['Project_ID']}/"
            f"{assigned_to(data, project)[0]}"
        )
    ).status_code == 204
    ranked = (
        await client.get("/api/v1/results/?event_id=asm&award_group=Example%20award")
    ).json()
    row = next(row for row in ranked if row["Project_ID"] == project["Project_ID"])
    assert row["Provisional"] and row["Rank"] == 0 and row["Judge_Count"] == 1


@pytest.mark.asyncio
async def test_affiliation_minimum_choices_and_login_limit(context):
    from app.services.voting import _attempts

    data = await voting_setup(context)
    client = data["client"]
    issued, headers = await voter_credentials(data, Affiliation_Confirmed=False)
    url = f"/api/v1/voting/rounds/{data['round']['Round_ID']}/ballot"
    body = {"Project_IDs": [data["projects"][0]["Project_ID"]]}
    assert (await client.post(url, headers=headers, json=body)).status_code == 409
    assert (
        await client.put(
            f"/api/v1/voting/admin/voters/{issued['voter']['Voter_ID']}",
            json={"Affiliation_Confirmed": True, "Presenter_Project_IDs": []},
        )
    ).status_code == 200
    assert (await client.post(url, headers=headers, json=body)).status_code == 200
    assert (
        await client.patch(
            f"/api/v1/projects/{data['projects'][0]['Project_ID']}",
            json={"Voting_Eligible": False},
        )
    ).status_code == 409
    too_many = await client.post(
        "/api/v1/voting/admin/rounds",
        json={
            **data["round_body"],
            "Round_Name": "Impossible minimum",
            "Min_Choices": 4,
            "Max_Choices": 4,
        },
    )
    assert too_many.status_code == 201, too_many.text
    assert (
        await client.post(
            f"/api/v1/voting/admin/rounds/{too_many.json()['Round_ID']}/open"
        )
    ).status_code == 409
    _attempts.clear()
    try:
        for _ in range(8):
            assert (
                await client.post(
                    "/api/v1/voting/login", json={"access_code": "unknown-code"}
                )
            ).status_code == 401
        assert (
            await client.post(
                "/api/v1/voting/login", json={"access_code": "unknown-code"}
            )
        ).status_code == 429
    finally:
        _attempts.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("aggregation", ["average", "total"])
async def test_manual_ties_stay_provisional(context, aggregation):
    data = await prepared(context)
    client = data["client"]
    await client.post("/api/v1/competition/asm/close")
    rules = {
        "Required_Reviews": 2,
        "Assignment_Only": True,
        "Aggregation": aggregation,
        "Tie_Policy": "manual",
        "Award_Groups": [],
        "Rules_Confirmed": True,
    }
    assert (
        await client.put("/api/v1/competition/asm/settings", json=rules)
    ).status_code == 200
    assert (await client.post("/api/v1/competition/asm/open")).status_code == 200
    for project in data["projects"][:2]:
        for judge_id in assigned_to(data, project):
            response = await client.post(
                f"/api/v1/judge/projects/{project['Project_ID']}/scores",
                headers=await judge_headers(data, judge_id),
                json=score_payload(data),
            )
            assert response.status_code == 200
    rows = (await client.get("/api/v1/results/?event_id=asm")).json()
    assert len(rows) == 2
    assert all(row["Rank"] == 1 and row["Tied"] and row["Provisional"] for row in rows)
    assert all(row["Total_Score"] == 12 and row["Average_Score"] == 6 for row in rows)


def test_prepare_rehearsal_is_repeatable_and_does_not_reset_operator_changes(tmp_path):
    import json
    import os
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    database = tmp_path / "rehearsal.db"
    credentials = tmp_path / "rehearsal-access.json"
    environment = {
        **os.environ,
        "GPSA_DATABASE_URL": f"sqlite+aiosqlite:///{database}",
        "GPSA_DEV_MODE": "true",
        "GPSA_SEED_HISTORICAL_EVENT": "false",
    }
    command = [
        sys.executable,
        "-m",
        "app.commands.prepare_competition",
        "--credentials",
        str(credentials),
    ]
    first = subprocess.run(
        command,
        env=environment,
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    first_result = json.loads(first.stdout)
    access = json.loads(credentials.read_text())
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT count(*) FROM Judge_Assignment").fetchone()[0] == 6
        db.execute(
            "DELETE FROM Judge_Assignment WHERE Assignment_ID = "
            "(SELECT min(Assignment_ID) FROM Judge_Assignment)"
        )
        db.commit()
    second = subprocess.run(
        command,
        env=environment,
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    assert first_result == json.loads(second.stdout)
    assert access == json.loads(credentials.read_text())
    assert credentials.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT count(*) FROM Judge_Assignment").fetchone()[0] == 5
        assert db.execute("SELECT count(*) FROM Project").fetchone()[0] == 3
        actual = db.execute(
            "SELECT Judging_Open, Rules_Confirmed, Required_Reviews, Award_Groups "
            "FROM Competition_Settings WHERE Event_ID=?",
            (access["asm_event_id"],),
        ).fetchone()
        assert actual == (0, 0, None, None)
        assert (
            db.execute(
                "SELECT count(*) FROM Voter WHERE Event_ID=?", (access["asm_event_id"],)
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT count(*) FROM Judge WHERE Event_ID=?", (access["asm_event_id"],)
            ).fetchone()[0]
            == 0
        )


def test_downgrade_refuses_to_discard_eligibility(tmp_path, monkeypatch):
    from pathlib import Path

    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.models.event import Event
    from app.models.project import Project

    database = tmp_path / "guard.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = sa.create_engine(f"sqlite:///{database}")
    with Session(engine) as db:
        db.add(
            Event(
                Event_ID="guard",
                Event_Name="Keep decisions",
                Event_Date=datetime.date(2026, 10, 31),
            )
        )
        db.flush()
        db.add(
            Project(
                Event_ID="guard",
                Project_Number="P-001",
                Project_Title="Retain eligibility",
                Presenter_First_Name="Test",
                Presenter_Last_Name="Presenter",
                Category="Poster",
                Judging_Eligible=False,
            )
        )
        db.commit()
    with pytest.raises(RuntimeError, match="eligibility"):
        command.downgrade(config, "20261027_roster_review")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                sa.text(
                    'SELECT count(*) FROM "Project" WHERE "Judging_Eligible" = FALSE'
                )
            )
            == 1
        )
        assert (
            connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
            == "20261027_competition"
        )
    engine.dispose()
