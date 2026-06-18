"""Extract plain text from an uploaded CV (PDF / DOCX / TXT)."""

from __future__ import annotations

from io import BytesIO


class CvExtractionError(RuntimeError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return _from_pdf(data)
    if ext in ("docx",):
        return _from_docx(data)
    if ext in ("txt", "md", "text", ""):
        return data.decode("utf-8", errors="ignore")
    # Best effort for anything else.
    return data.decode("utf-8", errors="ignore")


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise CvExtractionError("pypdf is required to read PDF CVs") from exc
    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def _from_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise CvExtractionError("python-docx is required to read DOCX CVs") from exc
    document = docx.Document(BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs).strip()
