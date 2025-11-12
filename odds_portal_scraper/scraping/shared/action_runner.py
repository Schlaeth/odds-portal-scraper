"""Utility to add retry/humanization behaviour around Playwright actions."""

from __future__ import annotations

from typing import Awaitable, Callable, Dict

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ...logger import logger

ActionCallable = Callable[[], Awaitable]


def create_action_runner(
    page: Page,
    action_delay_ms: int,
    retry_config: Dict[str, int],
    humanizer: Dict[str, Callable],
) -> Callable[[str, ActionCallable], Awaitable]:
    max_attempts = int(retry_config.get("max_attempts", 5))
    retry_delay = int(retry_config.get("delay_ms", 1000))
    before_action = humanizer.get("before_action") or (lambda *_: None)
    first_action = True

    async def wait_delay(delay_ms: int) -> None:
        if delay_ms > 0:
            await page.wait_for_timeout(delay_ms)

    async def runner(description: str, action: ActionCallable):
        nonlocal first_action
        if not first_action:
            await wait_delay(action_delay_ms)
        first_action = False

        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                await before_action(description)
                return await action()
            except PlaywrightTimeoutError as exc:
                last_error = exc
                if attempt == max_attempts:
                    break
                logger.warning(
                    "[%s] locator timed out (attempt %s/%s). Retrying in %sms.",
                    description,
                    attempt,
                    max_attempts,
                    retry_delay,
                )
                await wait_delay(retry_delay)
        raise last_error  # type: ignore[misc]

    return runner


__all__ = ["create_action_runner"]
