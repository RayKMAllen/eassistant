from pathlib import Path

from eassistant.services.storage import StorageService


def test_save_local_file(tmp_path: Path):
    """
    Tests that the StorageService can save a string to a local file.
    """
    storage_service = StorageService()
    content = "This is a test draft."
    file_path = tmp_path / "draft.txt"

    storage_service.save(content=content, file_path=str(file_path))

    assert file_path.exists()
    assert file_path.read_text() == content
