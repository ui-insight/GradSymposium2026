"""Admin final roster review, private preview and explicit organizer sign-off."""

import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.project import Project
from app.models.roster_review import RosterSignoff
from app.models.user import User
from app.schemas.project import ProjectUpdate
from app.schemas.roster_review import (
    DuplicateResolution,
    FinalRosterSignoff,
    RosterAction,
    RosterCorrection,
)
from app.services.project_changes import correct_project
from app.services.project_numbering import lock_event_numbers
from app.services.roster_import import COLUMNS, apply_changes, csv_text, plan_changes
from app.services.roster_review import (
    append_decision,
    apply_action,
    load_roster,
    workspace,
)

router = APIRouter(prefix="/roster-review", tags=["roster-review"])


def check_targets(state, targets):
    rows = {r["Project_ID"]: r for r in state["Rows"]}
    if len({t.Project_ID for t in targets}) != len(targets):
        raise HTTPException(422, "Review each presentation only once per action")
    for target in targets:
        if target.Project_ID not in rows:
            raise HTTPException(404, "Poster not found in this event")
        if target.Context != rows[target.Project_ID]["Context"]:
            raise HTTPException(409, "Roster details changed. Reload before confirming")


@router.get("/{event_id}")
async def get_roster(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await workspace(db, event_id)


@router.post("/{event_id}/decisions")
async def decisions(
    event_id: str,
    body: RosterAction,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, event_id)
    state = await workspace(db, event_id)
    check_targets(state, body.Targets)
    _, projects, _, latest, _ = await load_roster(db, event_id)
    by_id = {p.Project_ID: p for p in projects}
    if body.Superseded_By and (
        body.Action != "withdraw"
        or body.Superseded_By not in by_id
        or any(t.Project_ID == body.Superseded_By for t in body.Targets)
    ):
        raise HTTPException(
            422, "Choose a retained poster in this event, outside the withdrawals"
        )
    for target in body.Targets:
        await apply_action(
            db,
            by_id[target.Project_ID],
            body.Action,
            body.Reason,
            admin.Username,
            projects,
            latest,
            body.Superseded_By,
            body.Distinct_Verified,
            body.Talk_Only_Confirmed,
        )
    await db.commit()
    return await workspace(db, event_id)


@router.patch("/{event_id}/{project_id}/correction")
async def correction(
    event_id: str,
    project_id: str,
    body: RosterCorrection,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, event_id)
    state = await workspace(db, event_id)
    from app.schemas.roster_review import RosterTarget

    check_targets(state, [RosterTarget(Project_ID=project_id, Context=body.Context)])
    project = await db.get(Project, project_id)
    await correct_project(
        db,
        project,
        ProjectUpdate(
            **body.model_dump(exclude={"Context", "Reason"}, exclude_unset=True)
        ),
    )
    project.Roster_Review_Required = True
    await append_decision(db, project, "pending", body.Reason, admin.Username)
    await db.commit()
    return await workspace(db, event_id)


@router.post("/{event_id}/duplicates")
async def resolve_duplicates(
    event_id: str,
    body: DuplicateResolution,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, event_id)
    state = await workspace(db, event_id)
    check_targets(state, [body.Keep, body.Withdraw])
    pair = {body.Keep.Project_ID, body.Withdraw.Project_ID}
    group = next(
        (
            g
            for g in state["Duplicate_Groups"]
            if set(g["Project_IDs"]) == pair and g["Complete_Source"]
        ),
        None,
    )
    if not group or group["Later_ID"] != body.Keep.Project_ID:
        raise HTTPException(
            409,
            "Compare a complete duplicate pair and retain the verified later timestamp",
        )
    _, projects, _, latest, _ = await load_roster(db, event_id)
    by_id = {p.Project_ID: p for p in projects}
    if not by_id[body.Keep.Project_ID].Is_Active:
        raise HTTPException(409, "Reinstate the later version for review first")
    await apply_action(
        db,
        by_id[body.Withdraw.Project_ID],
        "withdraw",
        body.Reason,
        admin.Username,
        projects,
        latest,
        body.Keep.Project_ID,
    )
    _, projects, _, latest, _ = await load_roster(db, event_id)
    await apply_action(
        db,
        by_id[body.Keep.Project_ID],
        "accept",
        body.Reason,
        admin.Username,
        projects,
        latest,
        talk_only_confirmed=body.Talk_Only_Confirmed,
    )
    await db.commit()
    return await workspace(db, event_id)


@router.post("/{event_id}/signoff")
async def signoff(
    event_id: str,
    body: FinalRosterSignoff,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, event_id)
    state = await workspace(db, event_id)
    if body.Context != state["Context"]:
        raise HTTPException(409, "Roster changed. Review the final preview again")
    if (
        state["Blockers"]
        or body.Accepted_Count != state["Counts"]["Accepted"]
        or body.Source_Count != state["Counts"]["Source"]
    ):
        raise HTTPException(
            409,
            "Resolve pending decisions and reconcile the accepted/source counts first",
        )
    db.add(
        RosterSignoff(
            Event_ID=event_id,
            Context=state["Context"],
            Accepted_Count=body.Accepted_Count,
            Source_Count=body.Source_Count,
            Reference=body.Reference,
            Snapshot={
                "Counts": state["Counts"],
                "Sources": state["Sources"],
                "Preview": state["Preview"],
            },
            Signed_By=admin.Username,
            Signed_At=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )
    )
    await db.commit()
    return await workspace(db, event_id)


@router.post("/{event_id}/changes-csv")
async def upload_changes(
    event_id: str,
    file: UploadFile,
    dry_run: bool = True,
    context: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(422, "Upload a CSV smaller than 5 MiB")
    await lock_event_numbers(db, event_id)
    plan = await plan_changes(db, event_id, content)
    if dry_run:
        await db.rollback()
        return plan
    if plan["Context"] != context:
        raise HTTPException(
            409, "Roster or numbering changed. Preview the changes again"
        )
    if plan["Errors"] or not plan["Rows"]:
        raise HTTPException(422, "Resolve preview errors before applying any changes")
    return await apply_changes(db, event_id, plan, admin.Username)


@router.get("/{event_id}/template")
async def changes_template(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    state = await workspace(db, event_id)
    rows = [
        [
            r["Project_ID"],
            r["Project_Number"],
            "",
            r["Project_Title"],
            r["Presenter_Name"],
            r["Institution"] or "",
            r["Advisor_Name"] or "",
            r["Table_Number"] or "",
            (r["Source"] or {}).get("source_row", ""),
            (r["Source"] or {}).get("submitted_at", ""),
            (r["Source"] or {}).get("source_sha256", ""),
            ", ".join((r["Source"] or {}).get("flags") or []),
            r["Context"],
            "",
            "",
        ]
        for r in state["Rows"]
    ]
    return {"filename": "final-roster-changes.csv", "content": csv_text(COLUMNS, rows)}


@router.get("/{event_id}/report")
async def reconciliation_report(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    state = await workspace(db, event_id)
    content = f"# Final roster review: {state['Event_Name']}\n\n"
    content += ", ".join(f"{k}: {v}" for k, v in state["Counts"].items()) + ".\n\n"
    current = state["Signoff"]
    content += (
        f"Organizer sign-off: {current['Signed_By']}, {current['Signed_At']} UTC. "
        f"Current: {current['Current']}.\nReference: {current['Reference']}\n\n"
        if current
        else "Organizer sign-off pending.\n\n"
    )
    for group in state["Sources"]:
        content += (
            f"Source SHA-256: {group['SHA256']}; sheet: {group['Sheet']}; "
            f"rows: {len(group['Rows'])}; accepted {group['Accepted']}, "
            f"withdrawn {group['Withdrawn']}, pending {group['Pending']}.\n"
        )
    content += "\n## Accepted directory\n\n"
    for p in state["Preview"]["posters"]:
        content += (
            f"- {p['Project_Number']}: {p['Presenter_Display_Name']}, "
            f"{p['Project_Title']}\n"
        )
    return {"filename": "final-roster-review.md", "content": content}
