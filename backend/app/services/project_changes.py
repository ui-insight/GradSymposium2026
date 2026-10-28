"""Shared metadata and withdrawal operations, preserving permanent identities."""

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.models.competition import CompetitionSettings
from app.models.judge_assignment import JudgeAssignment
from app.models.voting_round import VotingRound
from app.schemas.project import ProjectCreate


async def correct_project(db, project, body):
    if (
        "Project_Number" in body.model_fields_set
        and body.Project_Number != project.Project_Number
    ):
        raise HTTPException(409, "Issued poster numbers cannot be changed")
    if "Category" in body.model_fields_set and body.Category != project.Category:
        raise HTTPException(409, "Numbered project categories cannot be changed")
    rules = await db.get(CompetitionSettings, project.Event_ID)
    if (
        rules
        and rules.Judging_Open
        and any(
            getattr(body, key) != getattr(project, key)
            for key in body.model_fields_set & {"Judging_Eligible", "Award_Groups"}
        )
    ):
        raise HTTPException(
            409, "Close judging before changing eligibility or award groups"
        )
    if (
        "Voting_Eligible" in body.model_fields_set
        and body.Voting_Eligible != project.Voting_Eligible
        and await db.scalar(
            select(VotingRound.Round_ID).where(
                VotingRound.Event_ID == project.Event_ID, VotingRound.Status == "open"
            )
        )
    ):
        raise HTTPException(
            409,
            "Close voting rounds before changing voting eligibility; "
            "use withdrawal for a withdrawal",
        )
    required = {"Project_Title", "Presenter_First_Name", "Presenter_Last_Name"}
    if any(getattr(body, field) is None for field in body.model_fields_set & required):
        raise HTTPException(422, "Required fields cannot be null")
    merged = {key: getattr(project, key) for key in ProjectCreate.model_fields}
    merged.update(body.model_dump(exclude_unset=True))
    try:
        validated = ProjectCreate.model_validate(merged)
        if "Award_Groups" in body.model_fields_set:
            body.Award_Groups = validated.Award_Groups
    except ValueError as exc:
        raise HTTPException(422, "Provide a title and presenter name") from exc
    roster_fields = set(ProjectCreate.model_fields) - {
        "Event_ID",
        "Judging_Eligible",
        "Voting_Eligible",
        "Award_Groups",
    }
    roster_changed = any(
        getattr(body, key) != getattr(project, key)
        for key in body.model_fields_set & roster_fields
    )
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    if roster_changed:
        project.Is_Published = False


async def withdraw_project(db, project):
    project.Is_Active = False
    project.Is_Published = False
    await db.execute(
        delete(JudgeAssignment).where(JudgeAssignment.Project_ID == project.Project_ID)
    )
