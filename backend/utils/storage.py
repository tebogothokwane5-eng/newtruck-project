import os
import boto3
from botocore.client import Config

R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT_URL]):
            raise RuntimeError("R2 storage environment variables are not fully set")

        _s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )
    return _s3_client


def upload_file(file_obj, key: str, content_type: str = None) -> str:
    """
    Upload a file-like object to R2 under the given key (path/filename).
    Returns the public URL of the uploaded file.
    """
    client = get_s3_client()

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.upload_fileobj(
        file_obj,
        R2_BUCKET_NAME,
        key,
        ExtraArgs=extra_args
    )

    return f"{R2_PUBLIC_URL}/{key}"


def delete_file(key: str):
    client = get_s3_client()
    client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
