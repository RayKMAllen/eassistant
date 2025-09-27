from pathlib import Path


class StorageService:
    """
    A service for handling storage operations, like saving files.
    """

    def save(self, content: str, file_path: str) -> None:
        """
        Saves a string content to a specified local file path.

        Args:
            content: The string content to save.
            file_path: The path to the file where the content will be saved.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
