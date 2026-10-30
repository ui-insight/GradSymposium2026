"""Judge QR lifecycle and cookie-backed public ballots through real routes."""

import asyncio
import datetime
import uuid

import httpx
import pytest
from sqlalchemy import func, select
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.api.deps import get_current_admin
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_invite import JudgeInvite
from app.models.voter import Voter
from app.services.voting import _attempts

context = poster_context


@pytest.mark.asyncio
async def test_personal_judge_qr_activation_and_recovery(context):
    client, sessions, app = context
    for _ in range(6):
        await create(client, Judging_Eligible=True, Voting_Eligible=True)
    rules = {
        "Required_Reviews": 3,
        "Assignment_Only": True,
        "Aggregation": "average",
        "Tie_Policy": "shared",
        "Award_Groups": [],
        "Rules_Confirmed": True,
    }
    assert (
        await client.put("/api/v1/competition/asm/settings", json=rules)
    ).status_code == 200
    body = {"Event_ID": "asm", "Request_ID": str(uuid.uuid4()), "Assignment_Limit": 4}
    response = await client.post("/api/v1/judge-checkin/admin", json=body)
    assert response.status_code == 201, response.text
    invite = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert (
        not invite["Activated"]
        and not invite["Is_Active"]
        and invite["Assignment_Count"] == 0
    )
    assert (await client.post("/api/v1/judge-checkin/admin", json=body)).json()[
        "Invite_ID"
    ] == invite["Invite_ID"]
    assert (
        await client.post(
            "/api/v1/judge/login", json={"access_code": invite["Access_Code"]}
        )
    ).status_code == 403
    token = {"token": invite["token"]}
    assert (await client.post("/api/v1/judge-checkin/inspect", json=token)).json() == {
        "activated": False
    }
    assert (
        await client.get(
            "/api/v1/judge/me", headers={"Authorization": "Bearer " + invite["token"]}
        )
    ).status_code == 401
    for names in (
        {"First_Name": " ", "Last_Name": "Judge"},
        {"First_Name": "A" * 101, "Last_Name": "Judge"},
    ):
        assert (
            await client.post("/api/v1/judge-checkin/activate", json={**token, **names})
        ).status_code == 422
    responses = await asyncio.gather(
        *[
            client.post(
                "/api/v1/judge-checkin/activate",
                json={**token, "First_Name": " Ada ", "Last_Name": " Rivera "},
            )
            for _ in range(2)
        ]
    )
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    activated = responses[0].json()
    assert activated["First_Name"] == "Ada"
    headers = {"Authorization": "Bearer " + activated["access_token"]}
    assigned = [
        p
        for p in (await client.get("/api/v1/judge/projects", headers=headers)).json()
        if p["is_assigned"]
    ]
    assert len(assigned) == 4
    assert sum(int(p["Project_Number"].split("-")[-1]) % 2 for p in assigned) == 2
    repeat = (
        await client.post(
            "/api/v1/judge-checkin/activate",
            json={**token, "First_Name": "Different", "Last_Name": "Name"},
        )
    ).json()
    assert repeat["First_Name"] == "Ada" and repeat["Judge_ID"] == activated["Judge_ID"]
    resumed = (await client.post("/api/v1/judge-checkin/inspect", json=token)).json()
    assert resumed["Judge_ID"] == activated["Judge_ID"]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(JudgeInvite)) == 1
        assert await db.scalar(select(func.count()).select_from(JudgeAssignment)) == 4
        judge = await db.get(Judge, activated["Judge_ID"])
        judge.Name_Confirmed_At = None
        await db.commit()
    assert (await client.post("/api/v1/judge-checkin/inspect", json=token)).json()[
        "name_confirmed"
    ] is False
    # An admin name correction must not turn an old QR into a second activation.
    repeat = (
        await client.post(
            "/api/v1/judge-checkin/activate",
            json={**token, "First_Name": "Again", "Last_Name": "Changed"},
        )
    ).json()
    assert repeat["First_Name"] == "Ada"
    await client.patch(
        "/api/v1/judges/" + activated["Judge_ID"], json={"Is_Active": False}
    )
    assert (
        await client.post("/api/v1/judge-checkin/inspect", json=token)
    ).status_code == 403
    app.dependency_overrides.pop(get_current_admin)
    assert (
        await client.get("/api/v1/judge-checkin/admin?event_id=asm")
    ).status_code == 401
    assert (
        await client.post("/api/v1/judge-checkin/admin", json=body)
    ).status_code == 401


async def open_round(client, name, public=True, kind="poster"):
    now = datetime.datetime.now(datetime.timezone.utc)
    response = await client.post(
        "/api/v1/voting/admin/rounds",
        json={
            "Event_ID": "asm",
            "Round_Name": name,
            "Public_Browser": public,
            "Candidate_Type": kind,
            "Min_Choices": 1,
            "Max_Choices": 1,
            "Ranked": False,
            "Allow_Self_Votes": True,
            "Allow_Edits": False,
            "Rules_Confirmed": True,
            "Opens_At": (now - datetime.timedelta(hours=1)).isoformat(),
            "Closes_At": (now + datetime.timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_browser_identity_reloads_and_one_ballot_per_round(context, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "dev_mode", True)
    _attempts.clear()
    client, sessions, app = context
    posters = [await create(client, Voting_Eligible=True) for _ in range(2)]
    first = await open_round(client, "Poster choice")
    second = await open_round(client, "Talk choice", kind="talk")
    private = await open_round(client, "Code only", public=False)
    talk = (
        await client.post(
            f"/api/v1/voting/admin/rounds/{second['Round_ID']}/talks",
            json={"Presenter_Display_Name": "Synthetic Speaker"},
        )
    ).json()
    for round_ in (first, second, private):
        response = await client.post(
            f"/api/v1/voting/admin/rounds/{round_['Round_ID']}/open"
        )
        assert response.status_code == 200, response.text
    start = await client.post("/api/v1/voting/browser-session")
    assert start.json() == {"cookie_ready": False}
    assert (
        "HttpOnly" in start.headers["set-cookie"]
        and "SameSite=lax" in start.headers["set-cookie"]
    )
    assert start.headers["cache-control"] == "no-store"
    session = (await client.post("/api/v1/voting/browser-session")).json()
    assert session["cookie_ready"]
    headers = {"Authorization": "Bearer " + session["access_token"]}
    me = (await client.get("/api/v1/voting/me", headers=headers)).json()
    assert me["Browser_Only"] and len(me["rounds"]) == 2
    assert (
        await client.get(
            f"/api/v1/voting/rounds/{private['Round_ID']}/posters", headers=headers
        )
    ).status_code == 403
    path = f"/api/v1/voting/rounds/{first['Round_ID']}/ballot"
    payload = {"Project_IDs": [posters[0]["Project_ID"]]}
    response = await client.post(path, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert (await client.post(path, json=payload, headers=headers)).status_code == 200
    assert (
        await client.post(
            path, json={"Project_IDs": [posters[1]["Project_ID"]]}, headers=headers
        )
    ).status_code == 409
    # Reopening, refreshing tokens and parallel requests reuse the same cookie identity.
    refreshed = await asyncio.gather(
        *[client.post("/api/v1/voting/browser-session") for _ in range(3)]
    )
    token = refreshed[-1].json()["access_token"]
    assert (
        await client.get(path, headers={"Authorization": "Bearer " + token})
    ).json()["Project_IDs"] == payload["Project_IDs"]
    otherpath = f"/api/v1/voting/rounds/{second['Round_ID']}/ballot"
    assert (
        await client.post(
            otherpath, json={"Project_IDs": [talk["Candidate_ID"]]}, headers=headers
        )
    ).status_code == 200
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Voter)) == 1
    # Another browser gets its own ballot; IP addresses are not person identifiers.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as other:
        await other.post("/api/v1/voting/browser-session")
        token = (await other.post("/api/v1/voting/browser-session")).json()[
            "access_token"
        ]
        assert (
            await other.post(
                path, json=payload, headers={"Authorization": "Bearer " + token}
            )
        ).status_code == 200
    assert (
        await client.post(
            "/api/v1/voting/browser-session",
            headers={"Origin": "https://other.example"},
        )
    ).status_code == 403


@pytest.mark.asyncio
async def test_public_mode_cannot_be_misconfigured_or_mint_private_access(context):
    client, _, _ = context
    assert (await client.post("/api/v1/voting/browser-session")).status_code == 409
    response = await client.post(
        "/api/v1/voting/admin/rounds",
        json={
            "Event_ID": "asm",
            "Round_Name": "Invalid public",
            "Public_Browser": True,
            "Allow_Self_Votes": False,
            "Allow_Edits": False,
        },
    )
    assert response.status_code == 422
