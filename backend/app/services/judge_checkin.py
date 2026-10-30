"""Personal QR recovery and bounded, conflict-safe assignments on activation."""

import datetime

from sqlalchemy import select

from app.auth.jwt import create_access_token
from app.models.competition import CompetitionSettings
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.project import Project

UTC = datetime.timezone.utc


def invitation_token(invite):
    issued = invite.Issued_At
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=UTC)
    return create_access_token(
        invite.Invite_ID,
        "judge_invite",
        expires_delta=issued + datetime.timedelta(days=7) - datetime.datetime.now(UTC),
    )


async def assign_new_judge(db, judge, limit):
    rules = await db.get(CompetitionSettings, judge.Event_ID)
    if not rules or not rules.Required_Reviews:
        return 0
    projects = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == judge.Event_ID,
                Project.Is_Active.is_(True),
                Project.Judging_Eligible.is_(True),
                Project.Roster_Review_Required.is_(False),
            )
        )
    )
    pairs = (
        await db.execute(
            select(JudgeAssignment.Judge_ID, JudgeAssignment.Project_ID)
            .join(Project, Project.Project_ID == JudgeAssignment.Project_ID)
            .join(Judge, Judge.Judge_ID == JudgeAssignment.Judge_ID)
            .where(Project.Event_ID == judge.Event_ID, Judge.Is_Active.is_(True))
        )
    ).all()
    conflicts = set(
        (
            await db.execute(
                select(JudgeConflict.Judge_ID, JudgeConflict.Project_ID)
                .join(Project, Project.Project_ID == JudgeConflict.Project_ID)
                .where(Project.Event_ID == judge.Event_ID)
            )
        ).all()
    )
    counts = {
        p.Project_ID: sum(
            pid == p.Project_ID and (jid, pid) not in conflicts for jid, pid in pairs
        )
        for p in projects
    }
    candidates = [
        p
        for p in projects
        if (judge.Judge_ID, p.Project_ID) not in conflicts
        and counts[p.Project_ID] < rules.Required_Reviews
    ]
    # Spread the initial allocation across both odd/even poster sessions.
    candidates.sort(key=lambda p: (counts[p.Project_ID], p.Project_Number))
    odd, even = [], []
    for p in candidates:
        suffix = p.Project_Number.rsplit("-", 1)[-1]
        (odd if suffix.isdigit() and int(suffix) % 2 else even).append(p)
    selected = []
    while (odd or even) and len(selected) < limit:
        for group in (odd, even):
            if group and len(selected) < limit:
                selected.append(group.pop(0))
    for project in selected:
        db.add(JudgeAssignment(Judge_ID=judge.Judge_ID, Project_ID=project.Project_ID))
    return len(selected)
