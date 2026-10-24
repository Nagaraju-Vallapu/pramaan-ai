import io
import shutil

import pymupdf as fitz
import pytest
from PIL import Image, ImageDraw

from app.services import document_processor
from app.services.document_processor import DocumentProcessingError, process_document
from app.services.ocr_service import ocr_image


def _pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 70), text)
    content = document.tobytes()
    document.close()
    return content


def test_processes_digital_pdf_and_extracts_labelled_fields():
    content = _pdf(
        "Institution Name: Pramaan Synthetic Institute\n"
        "Certificate Number: SYN-CERT-2026-001\n"
        "Issue Date: 01/01/2026\n"
        "Expiry Date: 31/12/2027\n"
        "Accreditation Category: Tier 1"
    )
    result = process_document("certificate.pdf", "application/pdf", content)
    assert result["status"] == "PROCESSED"
    assert result["pages"] == 1
    assert "Pramaan Synthetic Institute" in result["extracted_text"]
    fields = {field["name"]: field for field in result["fields"]}
    assert fields["institution_name"]["value"] == "Pramaan Synthetic Institute"
    assert fields["document_number"]["value"] == "SYN-CERT-2026-001"
    assert fields["expiry_date"]["value"] == "31/12/2027"
    assert fields["accreditation_category"]["value"] == "Tier 1"


def test_extracted_field_page_reference_is_correct_on_fourth_pdf_page():
    document = fitz.open()
    for text in (
        "A first page with enough content to prevent an OCR fallback.\nAdditional line.",
        "A second page with enough content to prevent an OCR fallback.\nAdditional line.",
        "A third page with enough content to prevent an OCR fallback.\nAdditional line.",
        "Expiry Date: 31/12/2027",
    ):
        page = document.new_page()
        page.insert_text((50, 70), text)
    content = document.tobytes()
    document.close()

    result = process_document("three-pages.pdf", "application/pdf", content)
    expiry = next(field for field in result["fields"] if field["name"] == "expiry_date")
    assert expiry["page"] == 4


def test_rejects_invalid_file_type_and_empty_content():
    with pytest.raises(DocumentProcessingError, match="Unsupported file extension"):
        process_document("report.exe", "application/octet-stream", b"not allowed")
    with pytest.raises(DocumentProcessingError, match="empty"):
        process_document("report.pdf", "application/pdf", b"")


def test_rejects_mismatched_content_and_corrupt_pdf():
    with pytest.raises(DocumentProcessingError, match="does not match a PDF"):
        process_document("report.pdf", "application/pdf", b"not a pdf")
    with pytest.raises(DocumentProcessingError, match="corrupt"):
        process_document("report.pdf", "application/pdf", b"%PDF-1.7 invalid payload")


def test_upload_size_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(document_processor, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(DocumentProcessingError, match="upload limit"):
        process_document("report.pdf", "application/pdf", b"%PDF-" + b"x" * 10)


def test_missing_tesseract_is_reported_without_fabricated_text(monkeypatch):
    monkeypatch.setattr(
        document_processor,
        "ocr_image",
        lambda _content: {
            "text": "",
            "confidence": None,
            "status": "OCR_UNAVAILABLE",
            "message": "Tesseract OCR is not installed or is missing from PATH.",
        },
    )
    image = Image.new("RGB", (200, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = process_document("scan.png", "image/png", buffer.getvalue())
    assert result["status"] == "OCR_UNAVAILABLE"
    assert result["extracted_text"] == ""
    assert all(field["value"] is None for field in result["fields"])


@pytest.mark.skipif(shutil.which("tesseract") is not None, reason="Tesseract is installed")
def test_real_missing_tesseract_result_is_explicit():
    image = Image.new("RGB", (200, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = ocr_image(buffer.getvalue())
    assert result["status"] == "OCR_UNAVAILABLE"
    assert "Tesseract OCR is not installed" in result["message"]


def test_ocr_text_is_grouped_by_line_for_field_extraction(monkeypatch):
    monkeypatch.setattr(
        document_processor,
        "ocr_image",
        lambda _content: {
            "text": "Institution Name: Pramaan Synthetic Institute\nCertificate Number: SYN-CERT-2026-001",
            "confidence": 91.0,
            "status": "PROCESSED",
        },
    )
    image = Image.new("RGB", (200, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = process_document("scan.png", "image/png", buffer.getvalue())
    fields = {field["name"]: field["value"] for field in result["fields"]}
    assert fields["institution_name"] == "Pramaan Synthetic Institute"
    assert fields["document_number"] == "SYN-CERT-2026-001"


def test_unreadable_ocr_is_marked_for_manual_review_without_invented_text(monkeypatch):
    monkeypatch.setattr(
        document_processor,
        "ocr_image",
        lambda _content: {
            "text": "",
            "confidence": None,
            "status": "NEEDS_MANUAL_REVIEW",
        },
    )
    image = Image.new("RGB", (200, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = process_document("blank.png", "image/png", buffer.getvalue())

    assert result["status"] == "NEEDS_MANUAL_REVIEW"
    assert result["extracted_text"] == ""
    assert all(field["value"] is None for field in result["fields"])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_ocr_image_when_tesseract_is_available():
    image = Image.new("RGB", (1200, 300), "white")
    ImageDraw.Draw(image).text((40, 80), "Institution Name: Synthetic College", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = process_document("scan.png", "image/png", buffer.getvalue())
    assert result["status"] in {"PROCESSED", "NEEDS_MANUAL_REVIEW"}
    assert result["metadata"]["ocr_used"] is True
