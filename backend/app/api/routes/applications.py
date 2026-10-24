import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import Principal, current_principal, require_roles
from app.models import Application, AuditEvent, Document, Finding, ValidationRun
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    AuditResponse,
    FindingResponse,
    ValidationRequest,
    ValidationResponse,
)
from app.services.audit_service import record_event
from app.services.validation_service import run_validation

router = APIRouter(prefix="/api", tags=["applications"])


def _get_application(db: Session, application_id: str) -> Application:
    application = db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.documents), selectinload(Application.validation_runs).selectinload(ValidationRun.findings))
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def _application_response(application: Application) -> ApplicationResponse:
    latest_run = max(application.validation_runs, key=lambda run: (run.created_at, run.id), default=None)
    return ApplicationResponse(
        id=application.id,
        institution_name=application.institution_name,
        name=application.institution_name,
        reference_number=application.reference_number,
        status=application.status,
        created_at=application.created_at,
        documents_count=len(application.documents),
        findings_count=len(latest_run.findings) if latest_run else 0,
    )


@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> dict:
    latest_runs = (
        select(
            ValidationRun.id.label("run_id"),
            func.row_number()
            .over(
                partition_by=ValidationRun.application_id,
                order_by=(ValidationRun.created_at.desc(), ValidationRun.id.desc()),
            )
            .label("latest_rank"),
        )
        .subquery()
    )
    return {
        "applications_count": db.scalar(select(func.count()).select_from(Application)) or 0,
        "documents_count": db.scalar(select(func.count()).select_from(Document)) or 0,
        "open_findings_count": db.scalar(
            select(func.count())
            .select_from(Finding)
            .join(latest_runs, Finding.validation_run_id == latest_runs.c.run_id)
            .where(latest_runs.c.latest_rank == 1, Finding.status == "OPEN")
        )
        or 0,
        "status_counts": {
            status: count
            for status, count in db.execute(
                select(Application.status, func.count()).group_by(Application.status)
            )
        },
    }


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> list[ApplicationResponse]:
    applications = db.scalars(
        select(Application)
        .order_by(Application.created_at.desc())
        .options(selectinload(Application.documents), selectinload(Application.validation_runs).selectinload(ValidationRun.findings))
    ).all()
    return [_application_response(application) for application in applications]


@router.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin")),
) -> ApplicationResponse:
    institution_name = payload.institution_name.strip()
    if not institution_name:
        raise HTTPException(status_code=422, detail="Institution name cannot be blank")
    application = Application(
        institution_name=institution_name,
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
    )
    db.add(application)
    db.flush()
    record_event(
        db,
        application.id,
        principal.username,
        "APPLICATION_CREATED",
        details={"reference_number": application.reference_number},
    )
    db.commit()
    db.refresh(application)
    return _application_response(application)


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> ApplicationResponse:
    return _application_response(_get_application(db, application_id))


@router.post("/applications/{application_id}/validate", response_model=ValidationResponse)
def validate_application(
    application_id: str,
    payload: ValidationRequest | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> ValidationResponse:
    application = _get_application(db, application_id)
    evaluation_date = payload.evaluation_date if payload and payload.evaluation_date else datetime.now(timezone.utc).date()
    run = run_validation(db, application, evaluation_date)
    application.status = (
        "REVIEW_REQUIRED"
        if run.status == "NEEDS_MANUAL_REVIEW"
        else "CHECKS_FLAGGED"
        if run.status == "FLAGGED"
        else "CHECKS_CLEAR"
    )
    record_event(
        db,
        application.id,
        principal.username,
        "VALIDATION_RUN",
        details={"run_id": run.id, "evaluation_date": evaluation_date.isoformat(), "status": run.status},
    )
    db.commit()
    db.refresh(run)
    return ValidationResponse(
        id=run.id,
        application_id=run.application_id,
        evaluation_date=run.evaluation_date,
        status=run.status,
        created_at=run.created_at,
        findings=[FindingResponse.model_validate(finding, from_attributes=True) for finding in run.findings],
    )


@router.get("/applications/{application_id}/findings", response_model=list[FindingResponse])
def list_findings(
    application_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> list[FindingResponse]:
    application = _get_application(db, application_id)
    latest_run = max(application.validation_runs, key=lambda run: (run.created_at, run.id), default=None)
    if latest_run is None:
        return []
    return [FindingResponse.model_validate(finding, from_attributes=True) for finding in latest_run.findings]


@router.get("/applications/{application_id}/audit", response_model=list[AuditResponse])
def list_audit_events(
    application_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> list[AuditResponse]:
    _get_application(db, application_id)
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.application_id == application_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        AuditResponse(
            id=event.id,
            application_id=event.application_id,
            document_id=event.document_id,
            action=event.action,
            actor=event.actor,
            details=json.loads(event.details_json),
            created_at=event.created_at,
        )
        for event in events
    ]
