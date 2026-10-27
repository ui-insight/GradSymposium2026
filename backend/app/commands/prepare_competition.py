"""Prepare pending ASM rules and an isolated synthetic dev rehearsal."""

import argparse
import asyncio
import datetime
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from app.commands.setup_asm import setup
from app.config import settings
from app.db.engine import async_session_factory, engine
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.voter import Voter
from app.models.voting_round import VotingRound
from app.services.access_code import generate_access_code
from app.services.project_numbering import lock_event_numbers, reserve_number
from app.services.voting import issue_code


def identifier(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "gpsa/asm-rehearsal/" + name))


async def prepare(credentials_path: Path):
    if not settings.dev_mode or settings.seed_historical_event:
        raise RuntimeError("Run only on dev with historical event seeding disabled")
    event_id = await setup(activate=True)
    credentials = (
        json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
    )
    async with async_session_factory() as db:
        if not await db.get(CompetitionSettings, event_id):
            db.add(CompetitionSettings(Event_ID=event_id))
        if not await db.scalar(
            select(Rubric.Rubric_ID).where(
                Rubric.Event_ID == event_id, Rubric.Category == "Poster"
            )
        ):
            db.add(
                Rubric(
                    Event_ID=event_id,
                    Rubric_Name="ASM poster rubric (awaiting confirmation)",
                    Category="Poster",
                    Max_Score=0,
                    Description=(
                        "No criteria or scale have been chosen for ASM. "
                        "Obtain Paul's approved rubric before confirming."
                    ),
                )
            )
        if not await db.scalar(
            select(VotingRound.Round_ID).where(VotingRound.Event_ID == event_id)
        ):
            db.add(
                VotingRound(
                    Event_ID=event_id,
                    Round_Name="ASM voting draft (rounds and rules pending)",
                )
            )
        await db.flush()
        demo_id = identifier("event")
        demo = await db.get(Event, demo_id)
        new_demo = demo is None
        if not demo:
            demo = Event(
                Event_ID=demo_id,
                Event_Name="Synthetic rehearsal (not the ASM competition)",
                Event_Date=datetime.date(2026, 10, 31),
                Event_End_Date=datetime.date(2026, 11, 1),
                Is_Active=False,
                Location="Dev rehearsal only",
                Description=(
                    "Three fictional presentations and example rules for testing. "
                    "Not award decisions or proposed ASM criteria."
                ),
            )
            db.add(demo)
            await db.flush()
        if not await db.get(CompetitionSettings, demo_id):
            db.add(
                CompetitionSettings(
                    Event_ID=demo_id,
                    Is_Rehearsal=True,
                    Required_Reviews=2,
                    Assignment_Only=True,
                    Aggregation="average",
                    Tie_Policy="shared",
                    Award_Groups=["Demonstration"],
                    Rules_Confirmed=True,
                    Judging_Open=True,
                )
            )
        rubric = await db.get(Rubric, identifier("rubric"))
        if not rubric:
            rubric = Rubric(
                Rubric_ID=identifier("rubric"),
                Event_ID=demo_id,
                Rubric_Name="Example rehearsal rubric (not ASM rules)",
                Category="Poster",
                Max_Score=9,
                Is_Locked=True,
            )
            db.add(rubric)
            await db.flush()
            for index, name in enumerate(
                (
                    "Example research criterion",
                    "Example presentation criterion",
                    "Example discussion criterion",
                )
            ):
                db.add(
                    RubricCriterion(
                        Rubric_ID=rubric.Rubric_ID,
                        Criterion_Name=name,
                        Criterion_Group="Synthetic example",
                        Min_Score=0,
                        Max_Score=3,
                        Sort_Order=index,
                    )
                )
        await lock_event_numbers(db, demo_id)
        for index in range(1, 4):
            project_id = identifier(f"project-{index}")
            if not await db.get(Project, project_id):
                number = await reserve_number(db, demo_id, project_id, "Poster")
                db.add(
                    Project(
                        Project_ID=project_id,
                        Event_ID=demo_id,
                        Project_Number=number,
                        Project_Title=f"Fictional demonstration poster {index}",
                        Presenter_First_Name="Demo",
                        Presenter_Last_Name=f"Presenter {index}",
                        Presenter_Display_Name=f"Demo Presenter {index}",
                        Institution="Synthetic test data",
                        Category="Poster",
                        Judging_Eligible=True,
                        Voting_Eligible=True,
                        Award_Groups=["Demonstration"],
                    )
                )
        await db.flush()
        judges = []
        for index in range(1, 4):
            judge = await db.get(Judge, identifier(f"judge-{index}"))
            if not judge:
                code = generate_access_code()
                while await db.scalar(
                    select(Judge.Judge_ID).where(Judge.Access_Code == code)
                ):
                    code = generate_access_code()
                judge = Judge(
                    Judge_ID=identifier(f"judge-{index}"),
                    Event_ID=demo_id,
                    First_Name="Demo",
                    Last_Name=f"Judge {index}",
                    Access_Code=code,
                )
                db.add(judge)
            judges.append(judge)
        await db.flush()
        for index in range(3) if new_demo else []:
            for judge_index in (index, (index + 1) % 3):
                project_id = identifier(f"project-{index + 1}")
                judge_id = judges[judge_index].Judge_ID
                if not await db.scalar(
                    select(JudgeAssignment.Assignment_ID).where(
                        JudgeAssignment.Judge_ID == judge_id,
                        JudgeAssignment.Project_ID == project_id,
                    )
                ):
                    db.add(JudgeAssignment(Judge_ID=judge_id, Project_ID=project_id))
        round_id = identifier("voting-round")
        if not await db.get(VotingRound, round_id):
            moment = datetime.datetime.now(datetime.timezone.utc)
            db.add(
                VotingRound(
                    Round_ID=round_id,
                    Event_ID=demo_id,
                    Round_Name="Example rehearsal ballot (not ASM rules)",
                    Status="open",
                    Min_Choices=1,
                    Max_Choices=2,
                    Ranked=False,
                    Allow_Self_Votes=False,
                    Allow_Edits=True,
                    Opens_At=moment - datetime.timedelta(minutes=5),
                    Closes_At=moment + datetime.timedelta(days=7),
                    Rules_Confirmed=True,
                )
            )
        voter = await db.get(Voter, identifier("voter"))
        if not voter:
            code, digest = issue_code()
            voter = Voter(
                Voter_ID=identifier("voter"),
                Event_ID=demo_id,
                Registration_Reference="synthetic-demo-attendee",
                Code_Hash=digest,
                Presenter_Project_IDs=[],
                Affiliation_Confirmed=True,
            )
            db.add(voter)
            credentials["voter_code"] = code
        elif not credentials.get("voter_code"):
            code, digest = issue_code()
            voter.Code_Hash = digest
            voter.Credential_Version += 1
            credentials["voter_code"] = code
        credentials.update(
            {
                "asm_event_id": event_id,
                "rehearsal_event_id": demo_id,
                "rehearsal_round_id": round_id,
                "judge_codes": [
                    {
                        "name": f"{judge.First_Name} {judge.Last_Name}",
                        "code": judge.Access_Code,
                    }
                    for judge in judges
                ],
            }
        )
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = credentials_path.with_suffix(".pending")
        temporary.write_text(json.dumps(credentials, indent=2))
        temporary.chmod(0o600)
        await db.commit()
        temporary.replace(credentials_path)
    await engine.dispose()
    return {
        "asm_event_id": event_id,
        "rehearsal_event_id": demo_id,
        "real_rules": "pending; judging and voting closed",
        "synthetic_projects": 3,
        "credentials_file": str(credentials_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(prepare(args.credentials.resolve())), indent=2))


if __name__ == "__main__":
    main()
