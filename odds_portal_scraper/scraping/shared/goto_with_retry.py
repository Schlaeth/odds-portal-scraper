"""Navigate to a URL with retry support for throttling errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from playwright.async_api import Page, Response

from ...logger import logger


@dataclass(frozen=True)
class RetryConfig:
    status_codes: tuple[int, ...] = (430,)
    max_attempts: int = 3
    wait_ms: int = 10_000


DEFAULT_RETRY = RetryConfig()


def _normalize_retry(config: Optional[Dict[str, int]]) -> RetryConfig:
    if not config:
        return DEFAULT_RETRY
    status_codes = tuple(config.get("status_codes", DEFAULT_RETRY.status_codes))
    max_attempts = int(config.get("max_attempts", DEFAULT_RETRY.max_attempts))
    wait_ms = int(config.get("wait_ms", DEFAULT_RETRY.wait_ms))
    return RetryConfig(status_codes=status_codes, max_attempts=max_attempts, wait_ms=wait_ms)


async def goto_with_retry(
    page: Page,
    url: str,
    *,
    goto_options: Optional[dict] = None,
    retry: Optional[Dict[str, int]] = None,
) -> Optional[Response]:
    config = _normalize_retry(retry)
    attempts = 0
    last_error: Exception | None = None

    while attempts < config.max_attempts:
        attempts += 1
        try:
            response = await page.goto(url, **(goto_options or {"wait_until": "domcontentloaded"}))
            status = response.status() if response else None
            if not status or status not in config.status_codes:
                return response
            last_error = RuntimeError(f"HTTP {status}")
            logger.warning(
                "Received status %s for %s (attempt %s/%s)",
                status,
                url,
                attempts,
                config.max_attempts,
            )
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            logger.warning("Navigation error for %s (attempt %s/%s): %s", url, attempts, config.max_attempts, exc)

        if attempts >= config.max_attempts:
            break

        await page.wait_for_timeout(config.wait_ms)

    raise RuntimeError(
        f"Failed to load {url} after {config.max_attempts} attempts: {last_error}"  # pragma: no cover - exception path
    )


__all__ = ["goto_with_retry", "RetryConfig"]
