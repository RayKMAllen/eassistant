from pathlib import Path

import boto3
from moto import mock_aws

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


@mock_aws
def test_save_s3_file():
    """
    Tests that the StorageService can upload a string to an S3 bucket.
    """
    # Setup mock S3
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-bucket"
    s3.create_bucket(Bucket=bucket_name)

    storage_service = StorageService()
    content = "This is an S3 test draft."
    file_key = "drafts/s3_draft.txt"

    storage_service.save(content=content, file_path=file_key, s3_bucket=bucket_name)

    # Verify the object was uploaded
    response = s3.get_object(Bucket=bucket_name, Key=file_key)
    assert response["Body"].read().decode("utf-8") == content
