from pathlib import Path
from typing import Optional

import boto3


class StorageService:
    """
    A service for handling storage operations, like saving files locally or to S3.
    """

    def __init__(self) -> None:
        self.s3_client = boto3.client("s3")

    def save(
        self,
        content: str,
        file_path: str,
        s3_bucket: Optional[str] = None,
    ) -> None:
        """
        Saves a string content to a specified local file path or an S3 bucket.

        Args:
            content: The string content to save.
            file_path: The local file path or S3 object key.
            s3_bucket: If provided, the content will be uploaded to this S3 bucket.
        """
        if s3_bucket:
            self.s3_client.put_object(
                Bucket=s3_bucket, Key=file_path, Body=content.encode("utf-8")
            )
        else:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
