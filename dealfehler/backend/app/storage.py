"""Medienspeicher: lokal (Entwicklung) oder S3-kompatibel (Produktion)."""
from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class Storage:
    def put(self, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError

    def get(self, key: str) -> bytes:
        raise NotImplementedError


class LocalStorage(Storage):
    def __init__(self, root: str, public_base: str):
        self.root = Path(root)
        self.public_base = public_base.rstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> str:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return f"{self.public_base}/media/{key}"

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


class S3Storage(Storage):
    def __init__(self):
        import boto3

        s = get_settings()
        self.bucket = s.s3_bucket
        self.public_base = (s.s3_public_base_url or "").rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            region_name=s.s3_region,
            aws_access_key_id=s.s3_access_key_id,
            aws_secret_access_key=s.s3_secret_access_key,
        )

    def put(self, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return f"{self.public_base}/{key}"

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(s.media_dir, s.api_base_url)
