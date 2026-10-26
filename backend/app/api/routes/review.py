from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, require_roles
from app.models import Application, Finding, ReviewAction, ValidationRun
from app.schemas import ReviewActionRequest, ReviewActionResponse
from app.services.audit_service import record_event

router = APIRouter(prefix="/api/findings", tags=["review"])


@router.post("/{finding_id}/actions", response_model=ReviewActionResponse, status_code=201)
def review_finding(
    finding_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin", "reviewer")),
) -> ReviewActionResponse:
    finding = db.scalar(select(Finding).where(Finding.id == finding_id))
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    run = db.get(ValidationRun, finding.validation_run_id)
    application = db.get(Application, run.application_id) if run else None
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    status_by_action = {
        "acknowledge": "ACKNOWLEDGED",
        "confirm": "CONFIRMED",
        "resolve": "RESOLVED",
        "request_correction": "CORRECTION_REQUESTED",
        "manual_verification": "MANUAL_VERIFICATION_REQUESTED",
    }
    finding.status = status_by_action[payload.action]
    action = ReviewAction(
        finding_id=finding.id,
        action=payload.action,
        note=payload.note.strip(),
        actor=principal.username,
    )
    db.add(action)
    record_event(
        db,
        application.id,
        principal.username,
        "FINDING_REVIEW_ACTION",
        document_id=finding.source_document_id,
        details={"finding_id": finding.id, "action": payload.action, "note": payload.note.strip()},
    )
    db.commit()
    db.refresh(action)
    return ReviewActionResponse(
        id=action.id,
        finding_id=action.finding_id,
        action=action.action,
        note=action.note,
        actor=action.actor,
        created_at=action.created_at,
    )
