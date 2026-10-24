import io

from PIL import Image

from app.core.config import TESSERACT_CMD


def ocr_image(content: bytes) -> dict:
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return {"text": "", "confidence": None, "status": "OCR_UNAVAILABLE", "message": "Install backend dependencies to enable OCR."}

    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    try:
        with Image.open(io.BytesIO(content)) as image:
            image = image.convert("RGB")
            data = pytesseract.image_to_data(image, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError:
        return {
            "text": "",
            "confidence": None,
            "status": "OCR_UNAVAILABLE",
            "message": "Tesseract OCR is not installed or is missing from PATH.",
        }
    except pytesseract.TesseractError as error:
        return {
            "text": "",
            "confidence": None,
            "status": "OCR_UNAVAILABLE",
            "message": f"Tesseract could not process this image (error {error.status}).",
        }

    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []
    for word, raw_confidence, block, paragraph, line in zip(
        data["text"],
        data["conf"],
        data["block_num"],
        data["par_num"],
        data["line_num"],
        strict=True,
    ):
        word = word.strip()
        try:
            word_confidence = float(raw_confidence)
        except ValueError:
            continue
        if not word or word_confidence < 0:
            continue
        lines.setdefault((block, paragraph, line), []).append(word)
        confidences.append(word_confidence)
    text = "\n".join(" ".join(words) for words in lines.values())
    confidence = sum(confidences) / len(confidences) if confidences else None
    status = "PROCESSED" if text and (confidence or 0) >= 50 else "NEEDS_MANUAL_REVIEW"
    return {"text": text, "confidence": confidence, "status": status}