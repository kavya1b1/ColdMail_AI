"""PDF text extraction helpers used by the Streamlit UI."""
from pathlib import Path
from typing import BinaryIO, Union

try:
    import pymupdf
except ImportError:  # Backward compatibility with older PyMuPDF installations.
    import fitz as pymupdf


def extract_text_from_pdf(pdf_source: Union[str, Path, BinaryIO, bytes]) -> str:
    """Extract text from a PDF path, uploaded file, file-like object, or bytes.

    Returns an ``[Error: ...]`` string so the existing Streamlit UI can display
    extraction failures without crashing the whole application.
    """
    try:
        if isinstance(pdf_source, (str, Path)):
            document = pymupdf.open(str(pdf_source))
        elif isinstance(pdf_source, bytes):
            document = pymupdf.open(stream=pdf_source, filetype="pdf")
        elif hasattr(pdf_source, "getvalue"):
            document = pymupdf.open(stream=pdf_source.getvalue(), filetype="pdf")
        elif hasattr(pdf_source, "read"):
            document = pymupdf.open(stream=pdf_source.read(), filetype="pdf")
        else:
            return "[Error: Unsupported PDF input type]"

        try:
            text = "\n".join(page.get_text("text") for page in document)
        finally:
            document.close()

        text = text.strip()
        return text if text else "[Error: No extractable text found in PDF]"
    except Exception as exc:
        return f"[Error: Could not extract PDF text: {exc}]"
