import asyncio
from pathlib import Path

import pytest

from odds_portal_scraper.exporters import export_to_dir, export_to_s3


@pytest.mark.asyncio
async def test_export_to_dir(tmp_path: Path):
    exporter = export_to_dir(tmp_path)
    data = {"key": "value"}
    await exporter(data, "sample.json")
    content = (tmp_path / "sample.json").read_text(encoding="utf-8")
    assert "key" in content


@pytest.mark.asyncio
async def test_export_to_s3(monkeypatch):
    calls = {}

    class FakeClient:
        def put_object(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr("odds_portal_scraper.exporters.boto3", "client", lambda *_: FakeClient())

    exporter = export_to_s3("bucket")
    await exporter({"a": 1}, "file.json")
    assert calls["Bucket"] == "bucket"
    assert calls["Key"] == "file.json"
    assert calls["ContentType"] == "application/json"
