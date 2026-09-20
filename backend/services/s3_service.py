"""Stores uploaded original documents in a private S3 bucket."""
import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_client = None


def is_configured():
    keys = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_BUCKET_NAME")
    return all(os.getenv(k) for k in keys)


def _get_client():
    global _client
    if _client is None:
        # boto3 reads the AWS_* variables from the environment (.env) by itself.
        _client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            config=Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 2}),
        )
    return _client


def upload_original(local_path, document_id, extension):
    """Upload the original file. Returns True on success. Never raises."""
    if not is_configured():
        return False
    try:
        with open(local_path, "rb") as f:
            _get_client().put_object(
                Bucket=os.getenv("S3_BUCKET_NAME"),
                Key=f"documents/{document_id}/original{extension}",
                Body=f,
                ContentType=CONTENT_TYPES.get(extension, "application/octet-stream"),
                ServerSideEncryption="AES256",
            )
        return True
    except (BotoCoreError, ClientError, OSError) as exc:
        logger.warning("S3 upload failed: %s", exc)
        return False