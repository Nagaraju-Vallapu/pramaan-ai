import io

import pymupdf as fitz
from PIL import Image

from app.api.routes import documents as documents_route


def _pdf(institution="Pramaan Synthetic Institute", certificate="SYN-CERT-2026-001", expiry="31/12/2027") -> bytes:
    document = fitz.open()
    page = document.new_page()
    certificate_line = f"Certificate Number: {certificate}\n" if certificate is not None else ""
    page.insert_textbox(
        fitz.Rect(40, 40, 550, 400),
        f"Institution Name: {institution}\n"
        f"{certificate_line}"
        f"Expiry Date: {expiry}\n"
        "This is a synthetic certificate for testing document processing end to end.",
        fontsize=13,
    )
    content = document.tobytes()
    document.close()
    return content


def test_health_endpoints_remain_available(client):
    assert client.get("/").json()["status"] == "running"
    assert client.get("/health").json()["status"] == "ok"


def test_authentication_is_required_and_roles_are_returned(client):
    assert client.get("/api/applications").status_code == 401
    response = client.post("/auth/login", json={"username": "reviewer", "password": "reviewer-change-me"})
    assert response.status_code == 200
    assert response.json()["role"] == "reviewer"


def test_application_upload_validation_and_audit_workflow(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Pramaan Synthetic Institute", "reference_number": "SYN-CERT-2026-001"},
    )
    assert created.status_code == 201
    assert created.json()["created_at"].endswith(("Z", "+00:00"))
    application_id = created.json()["id"]

    upload = client.post(
        f"/api/applications/{application_id}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("synthetic-certificate.pdf", io.BytesIO(_pdf()), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["status"] == "PROCESSED"
    assert document["fields"][0]["value"] == "Pramaan Synthetic Institute"

    validated = client.post(f"/api/applications/{application_id}/validate", headers=auth_headers, json={})
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "PASS"
    findings = client.get(f"/api/applications/{application_id}/findings", headers=auth_headers)
    assert findings.json() == []

    verified = client.post(f"/api/documents/{document['id']}/verify", headers=auth_headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["result"] == "MATCH"
    assert verified.json()["label"] == "SIMULATED — SYNTHETIC TEST DATA"

    events = client.get(f"/api/applications/{application_id}/audit", headers=auth_headers)
    assert {event["action"] for event in events.json()} >= {
        "APPLICATION_CREATED",
        "DOCUMENT_UPLOADED_AND_PROCESSED",
        "VALIDATION_RUN",
        "SIMULATED_ISSUER_VERIFICATION",
    }


def test_rejects_upload_with_invalid_mime(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Synthetic College"},
    )
    response = client.post(
        f"/api/applications/{created.json()['id']}/documents",
        headers=auth_headers,
        data={"document_type": "certificate"},
        files={"file": ("malicious.pdf", io.BytesIO(b"%PDF-1.7"), "image/png")},
    )
    assert response.status_code == 400
    assert "Content type" in response.json()["detail"]


def test_upload_api_rejects_empty_and_corrupt_files(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Upload Error Institute"},
    )
    application_id = created.json()["id"]
    for filename, content in (
        ("empty.pdf", b""),
        ("corrupt.pdf", b"%PDF-1.7 not a valid PDF document"),
    ):
        response = client.post(
            f"/api/applications/{application_id}/documents",
            headers=auth_headers,
            data={"document_type": "institution_certificate"},
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
        )
        assert response.status_code == 400
        assert response.json()["detail"]


def test_upload_api_enforces_streamed_size_limit(client, auth_headers, monkeypatch):
    monkeypatch.setattr(documents_route.config, "MAX_UPLOAD_BYTES", 32)
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Upload Size Institute"},
    )
    response = client.post(
        f"/api/applications/{created.json()['id']}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("large.pdf", io.BytesIO(b"%PDF-" + b"x" * 64), "application/pdf")},
    )
    assert response.status_code == 413
    assert "upload limit" in response.json()["detail"]


def test_upload_api_sanitizes_path_like_filename(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Filename Safety Institute"},
    )
    application_id = created.json()["id"]
    response = client.post(
        f"/api/applications/{application_id}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("..\\..\\outside.pdf", io.BytesIO(_pdf()), "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["original_filename"] == "outside.pdf"


def test_unreadable_image_upload_is_reviewable(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_processor.ocr_image",
        lambda _content: {"text": "", "confidence": None, "status": "NEEDS_MANUAL_REVIEW"},
    )
    image = Image.new("RGB", (200, 100), "white")
    content = io.BytesIO()
    image.save(content, format="PNG")
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Unreadable OCR Institute"},
    )
    application_id = created.json()["id"]
    upload = client.post(
        f"/api/applications/{application_id}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("blank.png", io.BytesIO(content.getvalue()), "image/png")},
    )
    assert upload.status_code == 201
    assert upload.json()["status"] == "NEEDS_MANUAL_REVIEW"
    assert upload.json()["extracted_text"] == ""
    validation = client.post(
        f"/api/applications/{application_id}/validate",
        headers=auth_headers,
        json={},
    )
    assert validation.json()["status"] == "NEEDS_MANUAL_REVIEW"
    assert any(item["rule_id"] == "LOW_CONFIDENCE_EXTRACTION" for item in validation.json()["findings"])


def test_document_download_requires_auth_and_returns_original_bytes(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Pramaan Synthetic Institute"},
    )
    application_id = created.json()["id"]
    content = _pdf()
    uploaded = client.post(
        f"/api/applications/{application_id}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("source.pdf", io.BytesIO(content), "application/pdf")},
    )
    document_id = uploaded.json()["id"]

    assert client.get(f"/api/documents/{document_id}/file").status_code == 401
    downloaded = client.get(f"/api/documents/{document_id}/file", headers=auth_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["content-disposition"].startswith("attachment;")


def test_validation_flags_expiry_mismatch_and_duplicate_upload(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Application Institute", "reference_number": "APP-REFERENCE"},
    )
    application_id = created.json()["id"]
    pdf = _pdf(
        institution="Document Institute",
        certificate="DOC-REFERENCE",
        expiry="31/12/2024",
    )
    for name in ("certificate.pdf", "duplicate.pdf"):
        response = client.post(
            f"/api/applications/{application_id}/documents",
            headers=auth_headers,
            data={"document_type": "institution_certificate"},
            files={"file": (name, io.BytesIO(pdf), "application/pdf")},
        )
        assert response.status_code == 201

    result = client.post(
        f"/api/applications/{application_id}/validate",
        headers=auth_headers,
        json={"evaluation_date": "2026-10-24"},
    )
    assert result.status_code == 200, result.text
    rule_ids = {finding["rule_id"] for finding in result.json()["findings"]}
    assert {"DOCUMENT_EXPIRED", "INSTITUTION_MISMATCH", "DUPLICATE_DOCUMENT"} <= rule_ids
    mismatch = next(item for item in result.json()["findings"] if item["rule_id"] == "INSTITUTION_MISMATCH")
    assert mismatch["source_document_id"]
    assert mismatch["source_filename"] == "certificate.pdf"
    assert mismatch["field_name"] == "institution_name"
    assert mismatch["page"] == 1
    assert mismatch["evidence"]


def test_missing_document_and_review_action_are_persisted(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Missing Document Institute"},
    )
    application_id = created.json()["id"]
    validation = client.post(
        f"/api/applications/{application_id}/validate",
        headers=auth_headers,
        json={},
    )
    assert validation.status_code == 200
    missing = next(item for item in validation.json()["findings"] if item["rule_id"] == "DOC_REQUIRED")
    reviewer = client.post(
        "/auth/login",
        json={"username": "reviewer", "password": "reviewer-change-me"},
    ).json()
    reviewer_headers = {"Authorization": f"Bearer {reviewer['access_token']}"}

    action = client.post(
        f"/api/findings/{missing['id']}/actions",
        headers=reviewer_headers,
        json={"action": "request_correction", "note": "Please upload a current certificate."},
    )
    assert action.status_code == 201
    assert action.json()["action"] == "request_correction"
    audit = client.get(f"/api/applications/{application_id}/audit", headers=auth_headers).json()
    assert any(item["action"] == "FINDING_REVIEW_ACTION" for item in audit)


def test_reruns_keep_latest_open_findings_count_stable(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Rerun Demo Institute"},
    )
    application_id = created.json()["id"]
    for _ in range(2):
        response = client.post(
            f"/api/applications/{application_id}/validate",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
    summary = client.get("/api/dashboard/summary", headers=auth_headers).json()
    assert summary["open_findings_count"] == 1


def test_missing_required_field_is_explicitly_manual_review(client, auth_headers):
    created = client.post(
        "/api/applications",
        headers=auth_headers,
        json={"institution_name": "Pramaan Synthetic Institute"},
    )
    uploaded = client.post(
        f"/api/applications/{created.json()['id']}/documents",
        headers=auth_headers,
        data={"document_type": "institution_certificate"},
        files={
            "file": (
                "missing-number.pdf",
                io.BytesIO(_pdf(certificate=None)),
                "application/pdf",
            )
        },
    )
    assert uploaded.status_code == 201
    result = client.post(
        f"/api/applications/{created.json()['id']}/validate",
        headers=auth_headers,
        json={},
    )
    assert result.json()["status"] == "NEEDS_MANUAL_REVIEW"
    missing = next(item for item in result.json()["findings"] if item["rule_id"] == "FIELD_REQUIRED")
    assert missing["field_name"] == "document_number"
    assert missing["manual_review_required"] is True


def test_admin_role_is_required_to_upload_or_create(client):
    reviewer = client.post(
        "/auth/login",
        json={"username": "reviewer", "password": "reviewer-change-me"},
    ).json()
    headers = {"Authorization": f"Bearer {reviewer['access_token']}"}
    response = client.post(
        "/api/applications",
        headers=headers,
        json={"institution_name": "Unauthorized Create"},
    )
    assert response.status_code == 403
    upload = client.post(
        "/api/applications/not-a-real-application/documents",
        headers=headers,
        data={"document_type": "institution_certificate"},
        files={"file": ("certificate.pdf", io.BytesIO(_pdf()), "application/pdf")},
    )
    assert upload.status_code == 403


def test_synthetic_issuer_mismatch_and_not_found_results(client, auth_headers):
    cases = (
        (
            "Pramaan Synthetic Institute",
            "Different Institution",
            "SYN-CERT-2026-001",
            "MISMATCH",
        ),
        (
            "Unknown Record Institute",
            "Unknown Record Institute",
            "SYN-NOT-FOUND-404",
            "NOT_FOUND",
        ),
    )
    for application_name, document_name, number, expected in cases:
        created = client.post(
            "/api/applications",
            headers=auth_headers,
            json={"institution_name": application_name},
        )
        application_id = created.json()["id"]
        uploaded = client.post(
            f"/api/applications/{application_id}/documents",
            headers=auth_headers,
            data={"document_type": "institution_certificate"},
            files={
                "file": (
                    "issuer-case.pdf",
                    io.BytesIO(_pdf(institution=document_name, certificate=number)),
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201
        verified = client.post(
            f"/api/documents/{uploaded.json()['id']}/verify",
            headers=auth_headers,
        )
        assert verified.status_code == 200
        assert verified.json()["result"] == expected
        assert verified.json()["source_type"] == "SIMULATED_SYNTHETIC_TEST_DATA"
