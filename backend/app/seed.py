import io
import json
from uuid import uuid4

import pymupdf as fitz
from PIL import Image
from sqlalchemy import select

from app.core.config import STORAGE_DIR
from app.core.database import SessionLocal, initialize_database
from app.models import Application, Document, ExtractedField
from app.services.audit_service import record_event
from app.services.document_processor import process_document


def _certificate(
    institution: str,
    number: str,
    expiry: str,
    *,
    future_metadata: bool = False,
    scanned: bool = False,
    missing_number: bool = False,
) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    if scanned:
        image = Image.new("RGB", (1200, 1600), "white")
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        page.insert_image(page.rect, stream=image_bytes.getvalue())
    else:
        page.insert_textbox(
            fitz.Rect(48, 48, 564, 500),
            "\n".join(
                [
                    "SYNTHETIC DEMONSTRATION CERTIFICATE",
                    f"Institution Name: {institution}",
                    *([] if missing_number else [f"Certificate Number: {number}"]),
                    "Issue Date: 01/01/2026",
                    f"Expiry Date: {expiry}",
                ]
            ),
            fontsize=13,
        )
    if future_metadata:
        metadata = pdf.metadata
        metadata["creationDate"] = "D:20991231000000"
        pdf.set_metadata(metadata)
    content = pdf.tobytes()
    pdf.close()
    return content


def _add_document(db, application: Application, filename: str, content: bytes) -> Document:
    processed = process_document(filename, "application/pdf", content)
    stored_filename = f"{uuid4().hex}.pdf"
    folder = STORAGE_DIR / application.id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / stored_filename).write_bytes(content)
    document = Document(
        application_id=application.id,
        original_filename=filename,
        stored_filename=stored_filename,
        document_type="institution_certificate",
        content_type="application/pdf",
        size_bytes=processed["size_bytes"],
        sha256=processed["sha256"],
        status=processed["status"],
        extracted_text=processed["extracted_text"],
        page_count=processed["pages"],
        metadata_json=json.dumps(processed["metadata"], ensure_ascii=True),
    )
    db.add(document)
    db.flush()
    for field in processed["fields"]:
        db.add(ExtractedField(document_id=document.id, **field))
    record_event(
        db,
        application.id,
        "demo-seed",
        "SYNTHETIC_DEMO_DOCUMENT_SEEDED",
        document_id=document.id,
        details={"filename": filename, "status": document.status},
    )
    return document


def seed_demo_data() -> None:
    initialize_database()
    scenarios = [
        ("DEMO-VALID", "Pramaan Synthetic Institute", "SYN-CERT-2026-001", "31/12/2027", {}),
        ("DEMO-MISSING", "Missing Document Demo Institute", "", "", {"missing": True}),
        ("DEMO-MISSING-FIELD", "Missing Field Demo Institute", "", "31/12/2027", {"missing_number": True}),
        ("DEMO-EXPIRED", "Demo Technical College", "SYN-CERT-2026-002", "31/12/2024", {}),
        ("DEMO-MISMATCH", "Pramaan Synthetic Institute", "SYN-CERT-2026-002", "31/12/2027", {"document_institution": "Different Synthetic Institute"}),
        ("DEMO-DUPLICATE", "Duplicate Upload Demo Institute", "SYN-CERT-2026-001", "31/12/2027", {"duplicate": True}),
        ("DEMO-METADATA", "Metadata Review Demo Institute", "SYN-CERT-2026-001", "31/12/2027", {"future_metadata": True}),
        ("DEMO-MANUAL", "Manual Review Demo Institute", "SYN-CERT-2026-001", "31/12/2027", {"scanned": True}),
        ("DEMO-UNKNOWN", "Demo Technical College", "SYN-NOT-FOUND-2026-404", "31/12/2027", {}),
    ]
    db = SessionLocal()
    try:
        for reference, institution, number, expiry, options in scenarios:
            existing = db.scalar(select(Application).where(Application.reference_number == reference))
            if existing:
                continue
            application = Application(institution_name=institution, reference_number=reference)
            db.add(application)
            db.flush()
            if options.get("missing"):
                record_event(
                    db,
                    application.id,
                    "demo-seed",
                    "SYNTHETIC_DEMO_APPLICATION_SEEDED",
                    details={"scenario": "missing required document"},
                )
                continue
            document_institution = options.get("document_institution", institution)
            content = _certificate(
                document_institution,
                number,
                expiry,
                future_metadata=options.get("future_metadata", False),
                scanned=options.get("scanned", False),
                missing_number=options.get("missing_number", False),
            )
            document = _add_document(db, application, f"{reference.lower()}-certificate.pdf", content)
            if options.get("duplicate"):
                duplicate = _add_document(db, application, f"{reference.lower()}-duplicate.pdf", content)
                duplicate.document_type = "supporting_copy"
            record_event(
                db,
                application.id,
                "demo-seed",
                "SYNTHETIC_DEMO_APPLICATION_SEEDED",
                details={"scenario": reference.removeprefix("DEMO-").lower()},
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Synthetic demo scenarios are ready.")


if __name__ == "__main__":
    seed_demo_data()
