import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core import config
from app.core.database import get_db
from app.core.security import Principal, current_principal, require_roles
from app.models import Application, Document, ExtractedField, VerificationRecord
from app.schemas import DocumentResponse, ExtractedFieldResponse, VerificationResponse
from app.services.audit_service import record_event
from app.services.document_processor import DocumentProcessingError, process_document
from app.services.verification_service import run_synthetic_verification

router = APIRouter(prefix="/api", tags=["documents"])


def _get_document(db: Session, document_id: str) -> Document:
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.fields))
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        application_id=document.application_id,
        original_filename=document.original_filename,
        document_type=document.document_type,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        sha256=document.sha256,
        status=document.status,
        extracted_text=document.extracted_text,
        pages=document.page_count,
        created_at=document.created_at,
        fields=[
            ExtractedFieldResponse(
                id=field.id,
                name=field.name,
                value=field.value,
                confidence=field.confidence,
                status=field.status,
                page=field.page,
            )
            for field in document.fields
        ],
        metadata=json.loads(document.metadata_json),
    )


@router.get("/documents/{document_id}/file")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> FileResponse:
    document = _get_document(db, document_id)
    storage_root = (config.STORAGE_DIR / document.application_id).resolve()
    try:
        stored_path = (storage_root / document.stored_filename).resolve(strict=True)
        stored_path.relative_to(storage_root)
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Stored document is unavailable") from error
    if not stored_path.is_file():
        raise HTTPException(status_code=404, detail="Stored document is unavailable")
    return FileResponse(
        stored_path,
        media_type=document.content_type,
        filename=document.original_filename,
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/applications/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(min_length=2, max_length=80),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin")),
) -> DocumentResponse:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if not all(char.isalnum() or char in {"_", "-"} for char in document_type):
        raise HTTPException(status_code=422, detail="Document type may contain only letters, digits, hyphens, or underscores")

    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > config.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.",
            )
    try:
        processed = process_document(file.filename, file.content_type or "", bytes(content))
    except DocumentProcessingError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    finally:
        await file.close()

    suffix = Path(processed["original_filename"]).suffix.lower()
    stored_filename = f"{uuid4().hex}{suffix}"
    application_dir = config.STORAGE_DIR / application.id
    stored_path = application_dir / stored_filename
    try:
        application_dir.mkdir(parents=True, exist_ok=True)
        with stored_path.open("xb") as output:
            output.write(content)
        document = Document(
            application_id=application.id,
            original_filename=processed["original_filename"],
            stored_filename=stored_filename,
            document_type=document_type,
            content_type=processed["content_type"],
            size_bytes=processed["size_bytes"],
            sha256=processed["sha256"],
            status=processed["status"],
            extracted_text=processed["extracted_text"],
            page_count=processed["pages"],
            metadata_json=json.dumps(processed["metadata"], ensure_ascii=True),
        )
        db.add(document)
        db.flush()
        for extracted in processed["fields"]:
            db.add(ExtractedField(document_id=document.id, **extracted))
        record_event(
            db,
            application.id,
            principal.username,
            "DOCUMENT_UPLOADED_AND_PROCESSED",
            document_id=document.id,
            details={
                "filename": document.original_filename,
                "document_type": document.document_type,
                "sha256": document.sha256,
                "status": document.status,
            },
        )
        db.commit()
        db.refresh(document)
        return _document_response(_get_document(db, document.id))
    except SQLAlchemyError as error:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not save the document record.") from error
    except OSError as error:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not store the uploaded document.") from error


@router.get("/applications/{application_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    application_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> list[DocumentResponse]:
    if db.get(Application, application_id) is None:
        raise HTTPException(status_code=404, detail="Application not found")
    documents = db.scalars(
        select(Document)
        .where(Document.application_id == application_id)
        .order_by(Document.created_at.desc())
        .options(selectinload(Document.fields))
    ).all()
    return [_document_response(document) for document in documents]


@router.post("/documents/{document_id}/verify", response_model=VerificationResponse)
def verify_document(
    document_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> VerificationResponse:
    document = _get_document(db, document_id)
    application = db.get(Application, document.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    record = run_synthetic_verification(db, application, document)
    record_event(
        db,
        application.id,
        principal.username,
        "SIMULATED_ISSUER_VERIFICATION",
        document_id=document.id,
        details={"result": record.result, "source_type": record.source_type},
    )
    db.commit()
    db.refresh(record)
    return VerificationResponse(
        id=record.id,
        application_id=record.application_id,
        document_id=record.document_id,
        source_type=record.source_type,
        result=record.result,
        compared_fields=json.loads(record.compared_fields_json),
        created_at=record.created_at,
    )


@router.get("/applications/{application_id}/verifications", response_model=list[VerificationResponse])
def list_verifications(
    application_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(current_principal),
) -> list[VerificationResponse]:
    if db.get(Application, application_id) is None:
        raise HTTPException(status_code=404, detail="Application not found")
    records = db.scalars(
        select(VerificationRecord)
        .where(VerificationRecord.application_id == application_id)
        .order_by(VerificationRecord.created_at.desc())
    ).all()
    return [
        VerificationResponse(
            id=record.id,
            application_id=record.application_id,
            document_id=record.document_id,
            source_type=record.source_type,
            result=record.result,
            compared_fields=json.loads(record.compared_fields_json),
            created_at=record.created_at,
        )
        for record in records
    ]
