from pathlib import Path


import pytest

from odds_portal_scraper.exporters import export_to_dir


@pytest.mark.asyncio
async def test_export_to_dir(tmp_path: Path):
    exporter = export_to_dir(tmp_path)
    data = {"key": "value"}
    await exporter(data, "sample.json")
    content = (tmp_path / "sample.json").read_text(encoding="utf-8")
    assert "key" in content
