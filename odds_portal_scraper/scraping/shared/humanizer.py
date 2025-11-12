"""Human-like interaction helpers for Playwright."""

from __future__ import annotations

import random
from typing import Any, Dict

from playwright.async_api import Page

HUMANIZE_DEFAULT = {
    "enabled": False,
    "scroll": {
        "probability": 0.35,
        "min_distance": 150,
        "max_distance": 600,
    },
    "mouse_move": {
        "probability": 0.65,
        "min_offset": 40,
        "max_offset": 180,
        "steps": {"min": 12, "max": 28},
    },
}


def merge_humanize_config(overrides: Dict[str, Any] | None) -> Dict[str, Any]:
    if not overrides:
        return HUMANIZE_DEFAULT

    merged = HUMANIZE_DEFAULT | overrides
    merged["scroll"] = HUMANIZE_DEFAULT["scroll"] | (overrides.get("scroll") or {})
    mouse_overrides = overrides.get("mouse_move") or {}
    steps = HUMANIZE_DEFAULT["mouse_move"]["steps"] | (mouse_overrides.get("steps") or {})
    merged["mouse_move"] = HUMANIZE_DEFAULT["mouse_move"] | mouse_overrides
    merged["mouse_move"]["steps"] = steps
    return merged


async def _noop(*_args, **_kwargs):
    return None


def create_humanizer(page: Page, config: Dict[str, Any]):
    if not config.get("enabled"):
        return {"before_action": _noop}

    state = {"initialized": False, "mouse": {"x": 0, "y": 0}}

    async def maybe_move_mouse() -> None:
        mouse_cfg = config.get("mouse_move") or {}
        if random.random() > mouse_cfg.get("probability", 0):
            return

        viewport = page.viewport_size() or {"width": 1280, "height": 720}
        if not state["initialized"]:
            state["initialized"] = True
            state["mouse"] = {"x": viewport["width"] // 2, "y": viewport["height"] // 2}
            await page.mouse.move(state["mouse"]["x"], state["mouse"]["y"], steps=5)

        min_offset = max(0, mouse_cfg.get("min_offset", 20))
        max_offset = max(min_offset + 1, mouse_cfg.get("max_offset", 150))
        offset_x = _random_signed_int(min_offset, max_offset)
        offset_y = _random_signed_int(min_offset, max_offset)

        steps_cfg = mouse_cfg.get("steps", {})
        min_steps = max(2, steps_cfg.get("min", 8))
        max_steps = max(min_steps + 1, steps_cfg.get("max", 20))
        steps = random.randint(min_steps, max_steps)

        target_x = _clamp(state["mouse"]["x"] + offset_x, 0, viewport["width"] - 1)
        target_y = _clamp(state["mouse"]["y"] + offset_y, 0, viewport["height"] - 1)

        await page.mouse.move(target_x, target_y, steps=steps)
        state["mouse"] = {"x": target_x, "y": target_y}

    async def maybe_scroll() -> None:
        scroll_cfg = config.get("scroll") or {}
        if random.random() > scroll_cfg.get("probability", 0):
            return

        min_distance = max(1, scroll_cfg.get("min_distance", 100))
        max_distance = max(min_distance + 1, scroll_cfg.get("max_distance", 400))
        distance = _random_signed_int(min_distance, max_distance)
        try:
            await page.evaluate("delta => window.scrollBy(0, delta)", distance)
        except Exception:
            pass

    async def before_action(_: str) -> None:
        await maybe_move_mouse()
        await maybe_scroll()

    return {"before_action": before_action}


def _random_signed_int(min_value: int, max_value: int) -> int:
    magnitude = random.randint(min_value, max_value)
    return magnitude if random.random() > 0.5 else -magnitude


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


__all__ = ["create_humanizer", "merge_humanize_config", "HUMANIZE_DEFAULT"]
