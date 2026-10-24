import json
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import RULES_PATH
from app.models import Application, Document, Finding, ValidationRun


def load_rules() -> dict:
    try:
        with RULES_PATH.open(encoding="utf-8") as rules_file:
            rules = json.load(rules_file)
    except OSError as error:
        raise RuntimeError(f"Could not read validation rules at {RULES_PATH}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Validation rules JSON is invalid") from error
    if not isinstance(rules, dict) or "rules" not in rules or "required_document_types" not in rules:
        raise RuntimeError("Validation rules must define rules and required_document_types")
    return rules


def _rule(rules: dict, rule_id: str) -> dict:
    try:
        return rules["rules"][rule_id]
    except KeyError as error:
        raise RuntimeError(f"Validation rule {rule_id} is not configured") from error


def _finding(
    rules: dict,
    rule_id: str,
    reason: str,
    *,
    document: Document | None = None,
    field_name: str | None = None,
    evidence: str | None = None,
    manual_review: bool = False,
) -> Finding:
    rule = _rule(rules, rule_id)
    return Finding(
        rule_id=rule_id,
        rule_name=rule["name"],
        severity=rule["severity"],
        reason=reason,
        source_document_id=document.id if document else None,
        source_filename=document.original_filename if document else None,
        page=next((field.page for field in document.fields if field.name == field_name), None) if document and field_name else None,
        field_name=field_name,
        evidence=evidence,
        recommended_action=rule["recommended_action"],
        manual_review_required=manual_review,
    )


def run_validation(db: Session, application: Application, evaluation_date: date) -> ValidationRun:
    rules = load_rules()
    documents = list(application.documents)
    findings: list[Finding] = []
    present_types = {document.document_type for document in documents}
    for required_type in rules["required_document_types"]:
        if required_type not in present_types:
            findings.append(
                _finding(
                    rules,
                    "DOC_REQUIRED",
                    f"Required illustrative document type '{required_type}' has not been uploaded.",
                    evidence=f"Expected document_type: {required_type}",
                )
            )

    for document in documents:
        fields = {field.name: field for field in document.fields}
        for required_field in rules.get("required_fields", []):
            extracted = fields.get(required_field)
            if extracted is None or not extracted.value:
                findings.append(
                    _finding(
                        rules,
                        "FIELD_REQUIRED",
                        f"Required field '{required_field}' could not be extracted.",
                        document=document,
                        field_name=required_field,
                        evidence=f"Page count: {document.page_count}; extraction status: {document.status}",
                        manual_review=True,
                    )
                )

        expiry = fields.get("expiry_date")
        if expiry and expiry.value:
            expiry_date = None
            for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %B %Y"):
                try:
                    expiry_date = date.fromisoformat(expiry.value) if date_format == "%Y-%m-%d" else datetime.strptime(expiry.value, date_format).date()
                    break
                except ValueError:
                    continue
            if expiry_date is None:
                findings.append(
                    _finding(
                        rules,
                        "DATE_UNPARSEABLE",
                        "The expiry date was extracted but its format could not be interpreted safely.",
                        document=document,
                        field_name="expiry_date",
                        evidence=expiry.value,
                        manual_review=True,
                    )
                )
            elif expiry_date < evaluation_date:
                findings.append(
                    _finding(
                        rules,
                        "DOCUMENT_EXPIRED",
                        f"Document expiry date {expiry_date.isoformat()} is before evaluation date {evaluation_date.isoformat()}.",
                        document=document,
                        field_name="expiry_date",
                        evidence=expiry.value,
                    )
                )

        institution = fields.get("institution_name")
        if institution and institution.value and institution.value.casefold() != application.institution_name.casefold():
            findings.append(
                _finding(
                    rules,
                    "INSTITUTION_MISMATCH",
                    "Extracted institution name does not match the application institution name.",
                    document=document,
                    field_name="institution_name",
                    evidence=f"Application: {application.institution_name}; document: {institution.value}",
                )
            )
        if document.status in {"OCR_UNAVAILABLE", "NEEDS_MANUAL_REVIEW"}:
            findings.append(
                _finding(
                    rules,
                    "LOW_CONFIDENCE_EXTRACTION",
                    f"Document processing status is {document.status}; extracted values require reviewer confirmation.",
                    document=document,
                    evidence=f"Processing status: {document.status}",
                    manual_review=True,
                )
            )
        for field in document.fields:
            if field.confidence is not None and field.confidence < float(rules.get("manual_review_confidence_below", 0.65)):
                findings.append(
                    _finding(
                        rules,
                        "LOW_CONFIDENCE_EXTRACTION",
                        f"Extracted field '{field.name}' has low confidence ({field.confidence:.2f}).",
                        document=document,
                        field_name=field.name,
                        evidence=field.value,
                        manual_review=True,
                    )
                )

        try:
            metadata = json.loads(document.metadata_json)
        except json.JSONDecodeError:
            metadata = {}
        for warning in metadata.get("warnings", []):
            findings.append(
                _finding(
                    rules,
                    "SUSPICIOUS_METADATA",
                    f"Document metadata indicator '{warning}' warrants review; it is not proof of tampering.",
                    document=document,
                    evidence=warning,
                    manual_review=True,
                )
            )

    hashes: dict[str, Document] = {}
    for document in documents:
        first = hashes.get(document.sha256)
        if first is None:
            hashes[document.sha256] = document
        else:
            findings.append(
                _finding(
                    rules,
                    "DUPLICATE_DOCUMENT",
                    f"This file is byte-for-byte identical to '{first.original_filename}'.",
                    document=document,
                    evidence=f"SHA-256: {document.sha256}",
                )
            )

    status = (
        "NEEDS_MANUAL_REVIEW"
        if any(finding.manual_review_required for finding in findings)
        else "FLAGGED"
        if findings
        else "PASS"
    )
    run = ValidationRun(
        application_id=application.id,
        evaluation_date=evaluation_date.isoformat(),
        status=status,
    )
    db.add(run)
    db.flush()
    for finding in findings:
        finding.validation_run_id = run.id
        db.add(finding)
    db.flush()
    return run