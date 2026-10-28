"""Known-answer closed-round reports, cutoff ties and consistent safe exports."""

import csv
import datetime
import hashlib
import io

import pytest
from sqlalchemy import func, select
from test_competition import judge_headers, voter_credentials, voting_setup
from test_poster_directory import context as poster_context
from test_poster_directory import create

from app.api.deps import get_current_admin
from app.models.ballot import Ballot
from app.models.ballot_selection import BallotSelection
from app.models.event import Event
from app.models.project import Project
from app.models.voter import Voter
from app.models.voting_round import VotingRound

context = poster_context


async def known_votes(context, counts):
    data = await voting_setup(context)
    while len(data["projects"]) < len(counts):
        data["projects"].append(
            await create(
                data["client"],
                Project_Title=f"Poster {len(data['projects']) + 1}",
                Presenter_Display_Name="Demo Presenter, Co Presenter",
                Voting_Eligible=True,
            )
        )
    async with data["sessions"]() as db:
        for index, (project, votes) in enumerate(zip(data["projects"], counts)):
            for vote in range(votes):
                reference = f"private-test-voter-{index}-{vote}"
                voter = Voter(
                    Event_ID="asm",
                    Registration_Reference=reference,
                    Code_Hash=hashlib.sha256(reference.encode()).hexdigest(),
                    Affiliation_Confirmed=True,
                )
                db.add(voter)
                await db.flush()
                ballot = Ballot(
                    Round_ID=data["round"]["Round_ID"], Voter_ID=voter.Voter_ID
                )
                db.add(ballot)
                await db.flush()
                db.add(
                    BallotSelection(
                        Ballot_ID=ballot.Ballot_ID, Project_ID=project["Project_ID"]
                    )
                )
        await db.commit()
    data["path"] = f"/api/v1/voting/admin/rounds/{data['round']['Round_ID']}"
    return data


async def closed_report(data):
    assert (await data["client"].post(data["path"] + "/close")).status_code == 200
    response = await data["client"].get(data["path"] + "/summary")
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_known_answer_cutoff_and_export_consistency(context):
    counts = [9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 1, 0, 0]
    data = await known_votes(context, counts)
    summary = await closed_report(data)
    report = summary["Top_Ten_Report"]
    assert report["Eligible_Count"] == 13
    assert [r["Votes"] for r in report["Top_Ten"]] == counts[:10]
    assert report["Cutoff_Spans_Ten"] and report["Cutoff_Votes"] == 1
    assert [r["Project_Number"] for r in report["Additional_Cutoff_Ties"]] == ["P-011"]
    assert [(r["Vote_Rank"], r["Tied_Count"]) for r in report["Top_Ten"][-2:]] == [
        (9, 3),
        (9, 3),
    ]
    assert report["Additional_Cutoff_Ties"][0]["Vote_Rank"] == 9
    assert [r["Votes"] for r in summary["tally"]] == counts
    exported = await data["client"].get(data["path"] + "/top-ten/export")
    assert exported.status_code == 200
    assert exported.headers["cache-control"] == "no-store"
    assert "attendee-choice-top-ten.csv" in exported.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 11
    for actual, expected in zip(
        rows, report["Top_Ten"] + report["Additional_Cutoff_Ties"]
    ):
        assert actual["Poster"] == expected["Project_Number"]
        assert actual["Presenter"] == expected["Presenter_Display_Name"]
        assert actual["Title"] == expected["Project_Title"]
        assert int(actual["Votes"]) == expected["Votes"]
        assert int(actual["Vote rank"]) == expected["Vote_Rank"]
        assert int(actual["Tied posters"]) == expected["Tied_Count"]
    assert [r["Report section"] for r in rows] == ["Top ten"] * 10 + [
        "Additional cutoff tie"
    ]
    assert [r["Cutoff tie"] for r in rows] == ["No"] * 8 + ["Yes"] * 3
    assert "private-test-voter" not in exported.text
    full = await data["client"].get(data["path"] + "/export")
    assert len(list(csv.DictReader(io.StringIO(full.text)))) == 13


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [3, 10, 13])
async def test_zero_votes_small_reports_and_zero_cutoff_tie(context, size):
    data = await known_votes(context, [0] * size)
    report = (await closed_report(data))["Top_Ten_Report"]
    assert len(report["Top_Ten"]) == min(size, 10)
    assert all(
        r["Votes"] == 0 and r["Vote_Rank"] == 1 and r["Tied_Count"] == size
        for r in report["Top_Ten"]
    )
    assert len(report["Additional_Cutoff_Ties"]) == max(0, size - 10)
    assert report["Cutoff_Spans_Ten"] == (size > 10)
    assert report["Cutoff_Votes"] == (0 if size >= 10 else None)


@pytest.mark.asyncio
async def test_no_cutoff_tie_and_tie_within_top_ten(context):
    data = await known_votes(context, [4, 4, 3, 3, 2, 2, 1, 1, 1, 1, 0])
    report = (await closed_report(data))["Top_Ten_Report"]
    assert not report["Cutoff_Spans_Ten"] and not report["Additional_Cutoff_Ties"]
    assert report["Top_Ten"][0]["Vote_Rank"] == report["Top_Ten"][1]["Vote_Rank"] == 1
    assert report["Top_Ten"][2]["Vote_Rank"] == 3


@pytest.mark.asyncio
async def test_hidden_before_close_and_revealed_at_expiry(context):
    data = await known_votes(context, [2, 1, 0])
    client = data["client"]
    summary = (await client.get(data["path"] + "/summary")).json()
    assert summary["Top_Ten_Report"] is None and summary["tally"] == []
    assert (await client.get(data["path"] + "/top-ten/export")).status_code == 409
    async with data["sessions"]() as db:
        round_ = await db.get(VotingRound, data["round"]["Round_ID"])
        round_.Closes_At = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(seconds=1)
        await db.commit()
    summary = (await client.get(data["path"] + "/summary")).json()
    assert (
        summary["Tallies_Available"]
        and summary["Top_Ten_Report"]["Top_Ten"][0]["Votes"] == 2
    )
    assert (await client.get(data["path"] + "/top-ten/export")).status_code == 200
    async with data["sessions"]() as db:
        round_ = await db.get(VotingRound, data["round"]["Round_ID"])
        round_.Status = "draft"
        await db.commit()
    assert (await client.get(data["path"] + "/summary")).json()[
        "Top_Ten_Report"
    ] is None
    assert (await client.get(data["path"] + "/top-ten/export")).status_code == 409


@pytest.mark.asyncio
async def test_current_eligibility_event_isolation_and_history_preserved(context):
    data = await known_votes(context, [3, 2, 1])
    client = data["client"]
    await closed_report(data)
    async with data["sessions"]() as db:
        (await db.get(Project, data["projects"][0]["Project_ID"])).Is_Active = False
        (
            await db.get(Project, data["projects"][1]["Project_ID"])
        ).Voting_Eligible = False
        # Revoked entitlements retain their submitted ballots under existing policy.
        voter = await db.scalar(
            select(Voter).where(
                Voter.Registration_Reference == "private-test-voter-2-0"
            )
        )
        voter.Is_Active = False
        db.add(
            Event(
                Event_ID="other",
                Event_Name="Other event",
                Event_Date=datetime.date(2026, 10, 31),
            )
        )
        await db.flush()
        db.add(
            Project(
                Project_ID="other-project",
                Event_ID="other",
                Project_Number="P-900",
                Project_Title="Other-event candidate",
                Presenter_First_Name="Other",
                Presenter_Last_Name="Presenter",
                Category="Poster",
                Voting_Eligible=True,
            )
        )
        await db.commit()
        before = [
            await db.scalar(select(func.count()).select_from(model))
            for model in (Ballot, BallotSelection)
        ]
    report = (await client.get(data["path"] + "/summary")).json()["Top_Ten_Report"]
    assert report["Eligible_Count"] == 1
    assert [(r["Project_Number"], r["Votes"]) for r in report["Top_Ten"]] == [
        ("P-003", 1)
    ]
    assert (await client.get(data["path"] + "/top-ten/export")).status_code == 200
    async with data["sessions"]() as db:
        assert (
            [
                await db.scalar(select(func.count()).select_from(model))
                for model in (Ballot, BallotSelection)
            ]
            == before
            == [6, 6]
        )
        (
            await db.get(Project, data["projects"][2]["Project_ID"])
        ).Voting_Eligible = False
        await db.commit()
    report = (await client.get(data["path"] + "/summary")).json()["Top_Ten_Report"]
    assert report["Eligible_Count"] == 0 and report["Top_Ten"] == []
    exported = await client.get(data["path"] + "/top-ten/export")
    assert len(list(csv.DictReader(io.StringIO(exported.text)))) == 0


@pytest.mark.asyncio
async def test_export_formula_safety_and_admin_only(context):
    data = await known_votes(context, [1, 0, 0])
    client = data["client"]
    await closed_report(data)
    async with data["sessions"]() as db:
        project = await db.get(Project, data["projects"][0]["Project_ID"])
        project.Presenter_Display_Name = "  =FORMULA(), Demo Co-presenter"
        project.Project_Title = '@HYPERLINK("example.org"), a title\nwith a newline'
        (
            await db.get(VotingRound, data["round"]["Round_ID"])
        ).Round_Name = "+Unsafe round"
        await db.commit()
    export = await client.get(data["path"] + "/top-ten/export")
    row = next(csv.DictReader(io.StringIO(export.text)))
    assert row["Presenter"].startswith("'  =") and row["Title"].startswith("'@")
    assert row["Round"].startswith("'+")
    assert "with a newline" in row["Title"]
    _, voter_headers = await voter_credentials(data)
    judge = await judge_headers(data, data["judges"][0]["Judge_ID"])
    data["app"].dependency_overrides.pop(get_current_admin)
    for headers in ({}, voter_headers, judge):
        for suffix in ("/summary", "/top-ten/export"):
            assert (
                await client.get(data["path"] + suffix, headers=headers)
            ).status_code == 401


@pytest.mark.asyncio
async def test_ranked_ballots_still_report_unweighted_counts(context):
    data = await voting_setup(context, Ranked=True)
    ids = [p["Project_ID"] for p in data["projects"]]
    data["path"] = f"/api/v1/voting/admin/rounds/{data['round']['Round_ID']}"
    for index, choices in enumerate(([ids[1], ids[0]], [ids[0], ids[2]])):
        _, headers = await voter_credentials(
            data, Registration_Reference=f"ranked-attendee-{index}"
        )
        response = await data["client"].post(
            f"/api/v1/voting/rounds/{data['round']['Round_ID']}/ballot",
            headers=headers,
            json={"Project_IDs": choices},
        )
        assert response.status_code == 200, response.text
    report = (await closed_report(data))["Top_Ten_Report"]
    assert [r["Votes"] for r in report["Top_Ten"]] == [2, 1, 1]
    assert [r["Vote_Rank"] for r in report["Top_Ten"]] == [1, 2, 2]
