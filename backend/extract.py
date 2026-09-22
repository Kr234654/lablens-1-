"""Reads the text out of an uploaded PDF."""
from io import BytesIO

from pypdf import PdfReader

MAX_PAGES = 30


class ReportError(Exception):
    """A problem with the uploaded report that we can explain to the user."""


def pdf_to_text(data: bytes) -> str:
    if not data.startswith(b"%PDF-"):
        raise ReportError("That file is not a PDF. Please upload a PDF report or paste the text instead.")
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ReportError("This PDF is password protected. Remove the password and try again.")
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((page.extract_text() or "") for page in pages)
    except ReportError:
        raise
    except Exception:
        raise ReportError("I could not read this PDF. Try another file, or paste the text of the report instead.")

    if len(text.strip()) < 20:
        raise ReportError(
            "This PDF has no readable text. It may be a scan or a photo. "
            "Please upload a PDF downloaded from the lab, or paste the text instead."
        )
    return text
