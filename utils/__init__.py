"""PDF text extraction utilities"""
import io
from typing import Optional


def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from uploaded PDF file."""
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.getvalue()))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except ImportError:
        return "[Error: PyPDF2 not installed. Run: pip install PyPDF2]"
    except Exception as e:
        return f"[Error reading PDF: {str(e)}]"
    