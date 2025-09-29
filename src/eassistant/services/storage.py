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
        target: str = "local",
        s3_bucket: Optional[str] = None,
    ) -> None:
        """
        Saves a string content to a specified local file path or an S3 bucket.

        Args:
            content: The string content to save.
            file_path: The local file path or S3 object key.
            target: The storage target, either "local" or "s3".
            s3_bucket: If target is "s3", the content will be uploaded to this bucket.
        """
        if target == "s3":
            if not s3_bucket:
                raise ValueError("s3_bucket must be provided for S3 target.")

            # If file_path is just a filename, save it to the 'outputs' directory
            s3_key = file_path
            if "/" not in s3_key and "\\" not in s3_key:
                s3_key = f"outputs/{s3_key}"

            self.s3_client.put_object(
                Bucket=s3_bucket, Key=s3_key, Body=content.encode("utf-8")
            )
        else:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
