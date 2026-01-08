"""Data export helpers."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

try:  # pragma: no cover - allow tests to run without boto3 installed
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = SimpleNamespace(client=None)  # type: ignore[assignment]

from botocore.exceptions import BotoCoreError, ClientError

from .logger import logger

CallbackType = Callable[[Any, str], Awaitable[None]]


def export_to_s3(bucket_name: str) -> CallbackType:
    """Return an async exporter that uploads JSON documents to S3."""

    if getattr(boto3, "client", None) is None:
        raise RuntimeError("boto3 is required for S3 exports. Install the 'boto3' package.")

    s3_client = boto3.client("s3")

    async def _export(data: Any, file_name: str) -> None:
        body = json.dumps(data).encode("utf-8")

        def _upload() -> None:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_name,
                Body=body,
                ContentType="application/json",
            )

        try:
            await asyncio.to_thread(_upload)
            logger.info("Uploaded %s to bucket %s", file_name, bucket_name)
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - requires AWS
            logger.error("Error uploading data to S3: %s", exc)
            raise

    return _export


def export_to_dir(directory: str | Path, *, skip_existing: bool = False) -> CallbackType:
    """Return an async exporter that writes JSON files locally."""

    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)

    async def _export(data: Any, file_name: str) -> None:
        destination = target_dir / file_name
        if skip_existing and destination.exists():
            logger.info("Skipping existing file %s", destination)
            return

        payload = json.dumps(data, ensure_ascii=False, indent=2)

        def _write() -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(payload, encoding="utf-8")

        await asyncio.to_thread(_write)
        logger.info("Wrote %s", destination)

    return _export


__all__ = ["export_to_dir", "export_to_s3", "CallbackType"]
