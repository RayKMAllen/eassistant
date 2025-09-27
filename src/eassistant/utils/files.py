from pathlib import Path
from typing import Union

from pypdf import PdfReader


def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    """
    Extracts text content from a PDF file.

    Args:
        file_path: The path to the PDF file.

    Returns:
        The extracted text content.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        # logger.error(f"Failed to extract text from PDF {file_path}: {e}")
        raise ValueError(f"Could not read PDF file at {file_path}") from e
