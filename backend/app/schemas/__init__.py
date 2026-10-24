from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ApplicationCreate(BaseModel):
    institution_name: str = Field(min_length=2, max_length=300)
    reference_number: str | None = Field(default=None, max_length=120)


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_name: str
    name: str
    reference_number: str | None
    status: str
    created_at: datetime
    documents_count: int = 0
    findings_count: int = 0


class ExtractedFieldResponse(BaseModel):
    id: str
    name: str
    value: str | None
    confidence: float | None
    status: str
    page: int | None


class DocumentResponse(BaseModel):
    id: str
    application_id: str
    original_filename: str
    document_type: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    extracted_text: str
    pages: int
    created_at: datetime
    fields: list[ExtractedFieldResponse]
    metadata: dict


class ValidationRequest(BaseModel):
    evaluation_date: date | None = None


class FindingResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str
    reason: str
    source_document_id: str | None
    source_filename: str | None
    page: int | None
    field_name: str | None
    evidence: str | None
    recommended_action: str
    manual_review_required: bool


class ValidationResponse(BaseModel):
    id: str
    application_id: str
    evaluation_date: str
    status: str
    created_at: datetime
    findings: list[FindingResponse]


class ReviewActionRequest(BaseModel):
    action: Literal["acknowledge", "confirm", "resolve", "request_correction", "manual_verification"]
    note: str = Field(default="", max_length=2000)


class ReviewActionResponse(BaseModel):
    id: str
    finding_id: str
    action: str
    note: str
    actor: str
    created_at: datetime


class VerificationResponse(BaseModel):
    id: str
    application_id: str
    document_id: str
    source_type: str
    label: str = "SIMULATED — SYNTHETIC TEST DATA"
    result: str
    compared_fields: list[dict]
    created_at: datetime


class AuditResponse(BaseModel):
    id: str
    application_id: str
    document_id: str | None
    action: str
    actor: str
    details: dict
    created_at: datetime