import json

from sqlalchemy.orm import Session

from app.core.config import ISSUER_DATA_PATH
from app.models import Application, Document, VerificationRecord


def run_synthetic_verification(
    db: Session,
    application: Application,
    document: Document,
) -> VerificationRecord:
    try:
        with ISSUER_DATA_PATH.open(encoding="utf-8") as issuer_file:
            records = json.load(issuer_file)
    except OSError as error:
        raise RuntimeError("Synthetic issuer test dataset is unavailable") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Synthetic issuer test dataset is invalid") from error

    fields = {field.name: field.value for field in document.fields}
    reference = fields.get("document_number")
    record = next((item for item in records if reference and item["document_number"] == reference), None)
    compared: list[dict] = []
    if not reference:
        result = "NEEDS_MANUAL_REVIEW"
    elif record is None:
        result = "NOT_FOUND"
        compared.append({"field": "document_number", "submitted": reference, "synthetic_record": None, "match": False})
    else:
        for key, submitted in (
            ("institution_name", fields.get("institution_name")),
            ("document_number", reference),
        ):
            expected = record.get(key)
            compared.append(
                {
                    "field": key,
                    "submitted": submitted,
                    "synthetic_record": expected,
                    "match": submitted is not None and submitted.casefold() == str(expected).casefold(),
                }
            )
        if any(item["submitted"] is None for item in compared):
            result = "NEEDS_MANUAL_REVIEW"
        elif all(item["match"] for item in compared):
            result = "MATCH"
        else:
            result = "MISMATCH"

    verification = VerificationRecord(
        application_id=application.id,
        document_id=document.id,
        result=result,
        compared_fields_json=json.dumps(compared, separators=(",", ":")),
    )
    db.add(verification)
    db.flush()
    return verification