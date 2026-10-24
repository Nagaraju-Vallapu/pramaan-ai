import json

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_event(
    db: Session,
    application_id: str,
    actor: str,
    action: str,
    *,
    document_id: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        application_id=application_id,
        document_id=document_id,
        actor=actor,
        action=action,
        details_json=json.dumps(details or {}, separators=(",", ":")),
    )
    db.add(event)
    return event
