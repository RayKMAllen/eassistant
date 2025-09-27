from pathlib import Path

import pytest

from eassistant.utils.files import extract_text_from_pdf


@pytest.fixture
def sample_pdf_path() -> Path:
    """Returns the path to a sample PDF file for testing."""
    return Path("tests/fixtures/sample.pdf")


def test_extract_text_from_pdf(sample_pdf_path: Path) -> None:
    """
    Tests that text can be successfully extracted from a sample PDF.
    """
    expected_text = "This is a test PDF file.It contains some sample text."
    extracted_text = extract_text_from_pdf(sample_pdf_path)
    # Normalize spacing and newlines for comparison
    normalized_extracted = "".join(extracted_text.split())
    normalized_expected = "".join(expected_text.split())
    assert normalized_extracted == normalized_expected


def test_extract_text_from_nonexistent_pdf() -> None:
    """
    Tests that a ValueError is raised when the PDF file does not exist.
    """
    with pytest.raises(ValueError, match="Could not read PDF file"):
        extract_text_from_pdf("nonexistent.pdf")
