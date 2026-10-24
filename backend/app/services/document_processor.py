import hashlib
import io
import re
from datetime import date, datetime, timezone
from pathlib import PurePath, PureWindowsPath

import pymupdf as fitz
from PIL import Image, UnidentifiedImageError

from app.core.config import MAX_UPLOAD_BYTES
from app.services.ocr_service import ocr_image

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
SUPPORTED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
MAX_IMAGE_PIXELS = 40_000_000


class DocumentProcessingError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def safe_original_filename(filename: str | None) -> str:
    name = PureWindowsPath(filename or "").name
    name = PurePath(name).name
    cleaned = "".join(char for char in name if char.isprintable() and char not in '<>:"/\\|?*')
    return cleaned[:255] or "upload"


def _validate_upload(filename: str | None, content_type: str, content: bytes) -> tuple[str, str]:
    name = safe_original_filename(filename)
    extension = PurePath(name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentProcessingError("Unsupported file extension; upload PDF, PNG, JPG, or JPEG.")
    expected_mime = SUPPORTED_MIME_TYPES[extension]
    actual_mime = content_type.split(";", 1)[0].strip().lower()
    if actual_mime != expected_mime:
        raise DocumentProcessingError(f"Content type must be {expected_mime} for this file.")
    if not content:
        raise DocumentProcessingError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentProcessingError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.", 413)
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise DocumentProcessingError("File content does not match a PDF.")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DocumentProcessingError("File content does not match a PNG image.")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise DocumentProcessingError("File content does not match a JPEG image.")
    return name, extension


def _field_value(text: str, labels: str) -> tuple[str | None, int | None]:
    pattern = re.compile(rf"(?im)^\s*(?:{labels})\s*[:#-]\s*(.{{2,160}}?)\s*$")
    match = pattern.search(text)
    if not match:
        return None, None
    value = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
    return (value, text.count("\n", 0, match.start()) + 1) if value else (None, None)


def extract_fields(pages: list[str], page_confidences: list[float | None]) -> list[dict]:
    full_text = "\n".join(pages)
    patterns = {
        "institution_name": r"(?:institution|college|university|institute)\s+name|name\s+of\s+(?:the\s+)?institution",
        "document_number": r"(?:certificate|document|registration|license|licence)\s*(?:no\.?|number|#)",
        "issue_date": r"(?:date\s+of\s+)?issue\s+date|issued\s+on|date\s+of\s+issue",
        "expiry_date": r"(?:date\s+of\s+)?(?:expiry|expiration)\s+date|valid\s+(?:until|upto|up to)",
    }
    fields: list[dict] = []
    reserved_labels = {
        "institution_name",
        "name_of_institution",
        "college_name",
        "university_name",
        "institute_name",
        "certificate_number",
        "certificate_no",
        "document_number",
        "document_no",
        "registration_number",
        "registration_no",
        "license_number",
        "licence_number",
        "issue_date",
        "date_of_issue",
        "issued_on",
        "expiry_date",
        "expiration_date",
        "valid_until",
        "valid_upto",
        "valid_up_to",
    }
    seen_labels: set[str] = set()
    for name, labels in patterns.items():
        value, line_number = _field_value(full_text, labels)
        page = None
        if value is not None and line_number is not None:
            page = 1
            consumed = 0
            for index, page_text in enumerate(pages, start=1):
                line_count = page_text.count("\n") + 1
                if line_number <= consumed + line_count:
                    page = index
                    break
                consumed += line_count
        confidence = None
        if value and page:
            ocr_confidence = page_confidences[page - 1]
            confidence = round(ocr_confidence / 100, 3) if ocr_confidence is not None else 0.9
        fields.append(
            {
                "name": name,
                "value": value,
                "confidence": confidence,
                "status": "EXTRACTED" if value else "NEEDS_MANUAL_REVIEW",
                "page": page,
            }
        )
    for page_number, page_text in enumerate(pages, start=1):
        for match in re.finditer(
            r"(?im)^\s*([a-z][a-z0-9 /_.()#-]{1,39})\s*:\s*(.{2,160}?)\s*$",
            page_text,
        ):
            label = re.sub(r"[^a-z0-9]+", "_", match.group(1).casefold()).strip("_")
            value = re.sub(r"\s+", " ", match.group(2)).strip(" .,:;-")
            if not value or label in reserved_labels or label in seen_labels:
                continue
            seen_labels.add(label)
            page_confidence = page_confidences[page_number - 1]
            fields.append(
                {
                    "name": label,
                    "value": value,
                    "confidence": round(page_confidence / 100, 3) if page_confidence is not None else 0.9,
                    "status": "EXTRACTED",
                    "page": page_number,
                }
            )
    return fields


def _metadata_warnings(metadata: dict) -> list[str]:
    warnings: list[str] = []
    raw_date = metadata.get("creationDate", "")
    date_match = re.search(r"D:(\d{4})(\d{2})(\d{2})", raw_date)
    if date_match:
        try:
            created = date(*map(int, date_match.groups()))
            if created > datetime.now(timezone.utc).date():
                warnings.append("metadata_creation_date_in_future")
        except ValueError:
            warnings.append("metadata_creation_date_unparseable")
    return warnings


def process_document(filename: str | None, content_type: str, content: bytes) -> dict:
    original_filename, extension = _validate_upload(filename, content_type, content)
    document_hash = hashlib.sha256(content).hexdigest()
    page_texts: list[str] = []
    page_confidences: list[float | None] = []
    processing_status = "PROCESSED"
    metadata: dict = {"warnings": [], "ocr_used": False}

    if extension == ".pdf":
        try:
            pdf = fitz.open(stream=content, filetype="pdf")
        except (fitz.FileDataError, RuntimeError, ValueError) as error:
            raise DocumentProcessingError("The PDF is corrupt or cannot be opened.") from error
        with pdf:
            if pdf.is_encrypted:
                raise DocumentProcessingError("Encrypted PDFs are not supported; upload an unlocked PDF.")
            if pdf.page_count == 0:
                raise DocumentProcessingError("The PDF contains no pages.")
            metadata.update(pdf.metadata or {})
            if pdf.page_count > 100:
                raise DocumentProcessingError("PDFs may contain at most 100 pages.", 413)
            for page in pdf:
                text = page.get_text("text").strip()
                if len(text) < 30:
                    page_area = page.rect.width * page.rect.height
                    scale = min(1.5, (MAX_IMAGE_PIXELS / page_area) ** 0.5)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    result = ocr_image(pixmap.tobytes("png"))
                    metadata["ocr_used"] = True
                    if result["status"] == "OCR_UNAVAILABLE":
                        processing_status = "OCR_UNAVAILABLE"
                        metadata["ocr_message"] = result.get("message")
                    elif result["text"]:
                        text = result["text"]
                        if result["status"] == "NEEDS_MANUAL_REVIEW":
                            processing_status = "NEEDS_MANUAL_REVIEW"
                    else:
                        processing_status = "NEEDS_MANUAL_REVIEW"
                    page_confidences.append(result.get("confidence"))
                else:
                    page_confidences.append(None)
                page_texts.append(text)
            metadata["warnings"] = _metadata_warnings(metadata)
    else:
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format != ({"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG"}[extension[1:]]):
                    raise DocumentProcessingError("File image format does not match its extension.")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise DocumentProcessingError("Image dimensions exceed the supported limit.", 413)
                image.verify()
            result = ocr_image(content)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            if isinstance(error, DocumentProcessingError):
                raise
            raise DocumentProcessingError("The image is corrupt or cannot be decoded.") from error
        metadata["ocr_used"] = True
        if result["status"] == "OCR_UNAVAILABLE":
            processing_status = "OCR_UNAVAILABLE"
            metadata["ocr_message"] = result.get("message")
        elif result["text"]:
            page_texts.append(result["text"])
            page_confidences.append(result.get("confidence"))
            if result["status"] == "NEEDS_MANUAL_REVIEW":
                processing_status = "NEEDS_MANUAL_REVIEW"
        else:
            processing_status = "NEEDS_MANUAL_REVIEW"

    text = "\n\n".join(page_texts)
    if not text and processing_status == "PROCESSED":
        processing_status = "NEEDS_MANUAL_REVIEW"
    return {
        "original_filename": original_filename,
        "content_type": SUPPORTED_MIME_TYPES[extension],
        "size_bytes": len(content),
        "sha256": document_hash,
        "status": processing_status,
        "extracted_text": text,
        "pages": len(page_texts),
        "fields": extract_fields(page_texts, page_confidences),
        "metadata": metadata,
    }