"""Admin-only mentor reconciliation using the existing conflict enforcement path."""

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge import Judge
from app.models.user import User
from app.schemas.mentor_review import MentorCompletion, MentorDecision
from app.services.competition import lock_event
from app.services.mentor_import import (
    DECISION_COLUMNS,
    JUDGE_COLUMNS,
    apply_import,
    csv_content,
    preview_import,
)
from app.services.mentor_review import apply_decision, review_workspace

router = APIRouter(prefix="/mentor-review", tags=["mentor-review"])


@router.post("/{event_id}/imports/{kind}")
async def upload_review(
    event_id: str,
    kind: str,
    file: UploadFile,
    dry_run: bool = True,
    context: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if kind not in {"judges", "decisions"}:
        raise HTTPException(404, "Import type not found")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(422, "Upload a CSV file smaller than 5 MiB")
    await lock_event(db, event_id)
    preview = await preview_import(db, event_id, kind, content)
    if dry_run:
        return preview
    if context != preview["Context"]:
        raise HTTPException(
            409, "Roster or review details changed. Preview the upload again"
        )
    if preview["Errors"] or not preview["Rows"]:
        raise HTTPException(
            422, "Resolve all preview errors before applying this upload"
        )
    return await apply_import(db, event_id, kind, preview, admin.Username)


@router.get("/{event_id}/template/{kind}")
async def download_template(
    event_id: str,
    kind: str,
    judge_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    workspace = await review_workspace(db, event_id, judge_id, include_coverage=False)
    if kind == "judges":
        content = csv_content(JUDGE_COLUMNS, [])
    elif kind == "decisions":
        judge = next(
            (j for j in workspace["Judges"] if j["Judge_ID"] == workspace["Judge_ID"]),
            None,
        )
        content = csv_content(
            DECISION_COLUMNS,
            [
                [
                    judge["Judge_ID"],
                    judge["Name"],
                    p["Project_Number"],
                    p["Presenter_Name"],
                    p["Advisor_Name"] or "",
                    p["Context"],
                    "",
                    "",
                ]
                for p in workspace["Projects"]
                if p["Is_Active"]
            ]
            if judge
            else [],
        )
    else:
        raise HTTPException(404, "Template type not found")
    return {"filename": f"mentor-{kind}.csv", "content": content}


@router.get("/{event_id}")
async def get_review(
    event_id: str,
    judge_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await review_workspace(db, event_id, judge_id)


@router.put("/{event_id}/{judge_id}/{project_id}")
async def save_decision(
    event_id: str,
    judge_id: str,
    project_id: str,
    body: MentorDecision,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    workspace = await review_workspace(db, event_id, judge_id)
    row = next(
        (r for r in workspace["Projects"] if r["Project_ID"] == project_id), None
    )
    if not row:
        raise HTTPException(404, "Presentation not found in this event")
    if body.Context != row["Context"]:
        raise HTTPException(
            409, "Review details changed. Reload before saving a decision"
        )
    if body.Decision == "clear" and row["Conflict_ID"] is not None:
        raise HTTPException(
            409, "Resolve the recorded conflict in Competition setup first"
        )
    await apply_decision(
        db, judge_id, project_id, body.Decision, body.Note, admin.Username
    )
    await db.commit()
    return await review_workspace(db, event_id, judge_id)


@router.post("/{event_id}/{judge_id}/complete")
async def complete_review(
    event_id: str,
    judge_id: str,
    body: MentorCompletion,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    workspace = await review_workspace(db, event_id, judge_id)
    if body.Context != workspace["Context"]:
        raise HTTPException(409, "Review details changed. Reload before finishing")
    if workspace["Completion_Blockers"]:
        raise HTTPException(409, "; ".join(workspace["Completion_Blockers"]))
    judge = await db.get(Judge, judge_id)
    judge.Conflict_Review_Required = False
    judge.Previous_Name = None
    await db.commit()
    return await review_workspace(db, event_id, judge_id)
