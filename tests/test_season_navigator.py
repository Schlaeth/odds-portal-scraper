import pytest

from odds_portal_scraper.scraping.historic.season_navigator import discover_season_pages


class FakeLocator:
    def __init__(self, anchors):
        self._anchors = anchors

    async def evaluate_all(self, *_args, **_kwargs):
        return self._anchors


class FakePage:
    def __init__(self, url, anchors, html=""):
        self.url = url
        self._anchors = anchors
        self._html = html

    async def goto(self, url, **_kwargs):
        self.url = url

    async def wait_for_load_state(self, *_args, **_kwargs):
        return None

    async def wait_for_timeout(self, *_args, **_kwargs):
        return None

    def locator(self, selector):
        return FakeLocator(self._anchors.get(selector, []))

    async def content(self):
        return self._html


@pytest.mark.asyncio
async def test_discover_season_pages_respects_start_page_filter():
    anchors = {
        "a[href*='#/page/']": [
            {"href": "#/page/1", "text": "1"},
            {"href": "#/page/2", "text": "2"},
            {"href": "#/page/3", "text": "3"},
        ]
    }
    page = FakePage("https://example.com/league/results/", anchors)

    result = await discover_season_pages(page, page.url, start_page=2)

    assert result == [
        "https://example.com/league/results/#/page/2",
        "https://example.com/league/results/#/page/3",
    ]


@pytest.mark.asyncio
async def test_discover_season_pages_skips_when_start_page_exceeds_available():
    page = FakePage("https://example.com/league/results/", {})

    result = await discover_season_pages(page, page.url, start_page=3)

    assert result == []
