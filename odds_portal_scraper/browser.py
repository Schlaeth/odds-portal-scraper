"""Custom Playwright browser wrapper used by the scraper."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from playwright.async_api import Browser as PwBrowser
from playwright.async_api import BrowserContext, Page, async_playwright

from .logger import logger

DESKTOP_VIEWPORTS = (
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1600, "height": 900},
    {"width": 1680, "height": 1050},
    {"width": 1920, "height": 1080},
)

TIMEZONE_IDS = (
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Madrid",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Prague",
    "Europe/Warsaw",
    "Europe/Athens",
    "Europe/Dublin",
    "America/Bogota",
    "America/Mexico_City",
)

LOCALE_OPTIONS = (
    "en-US",
    "en-GB",
    "en-CA",
    "en-AU",
    "fr-FR",
    "es-ES",
    "es-AR",
    "pt-PT",
    "pt-BR",
    "de-DE",
    "it-IT",
    "nl-NL",
)

COLOR_SCHEMES = ("light", "dark")
DEVICE_SCALE_FACTORS = (1, 1.25, 1.5, 2)
HARDWARE_CONCURRENCY_VALUES = (4, 6, 8, 12)
DEVICE_MEMORY_VALUES = (4, 8, 16)
CONNECTION_DOWNLINK_VALUES = (25, 35, 45, 55, 65, 75, 95)
CONNECTION_RTT_VALUES = (20, 30, 40, 50, 60)
USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/119.0 Safari/537.36",
)


def _pick(values):
    return random.choice(values)


def _build_language_list(locale: Optional[str]) -> List[str]:
    if not locale:
        return ["en-US", "en"]

    language, _, region = locale.partition("-")
    normalized = f"{language}-{region.upper()}" if region else language
    return list(dict.fromkeys([normalized, language]))


def _build_accept_language(locale: Optional[str]) -> str:
    languages = _build_language_list(locale)
    if len(languages) == 1:
        return languages[0]
    return f"{languages[0]},{languages[1]};q=0.9"


def _derive_navigator_metadata(user_agent: Optional[str]) -> Dict[str, str]:
    if not user_agent:
        return {
            "platform": "Win32",
            "vendor": "Google Inc.",
            "appVersion": "5.0 (Windows NT 10.0; Win64; x64)",
        }

    ua = user_agent
    if "Mac OS" in ua or "Macintosh" in ua:
        return {
            "platform": "MacIntel",
            "vendor": "Apple Computer, Inc.",
            "appVersion": "5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

    if "Linux" in ua and "Android" not in ua:
        return {
            "platform": "Linux x86_64",
            "vendor": "Google Inc.",
            "appVersion": "5.0 (X11; Linux x86_64)",
        }

    return {
        "platform": "Win32",
        "vendor": "Google Inc.",
        "appVersion": "5.0 (Windows NT 10.0; Win64; x64)",
    }


def _build_fingerprint(config: Dict[str, object]) -> Dict[str, object]:
    locale = config.get("locale") or _pick(LOCALE_OPTIONS)
    viewport = config.get("viewport") or _pick(DESKTOP_VIEWPORTS)
    color_scheme = config.get("color_scheme") or _pick(COLOR_SCHEMES)

    languages = _build_language_list(str(locale))
    metadata = _derive_navigator_metadata(str(config.get("user_agent")))

    return {
        "languages": languages,
        "acceptLanguage": _build_accept_language(str(locale)),
        "hardwareConcurrency": _pick(HARDWARE_CONCURRENCY_VALUES),
        "deviceMemory": _pick(DEVICE_MEMORY_VALUES),
        "maxTouchPoints": 0,
        "colorScheme": color_scheme,
        "viewport": viewport,
        "screen": {
            "width": viewport["width"],
            "height": viewport["height"],
            "availWidth": viewport["width"],
            "availHeight": viewport["height"],
            "colorDepth": 24,
            "pixelDepth": 24,
        },
        "navigator": metadata,
        "connection": {
            "downlink": _pick(CONNECTION_DOWNLINK_VALUES),
            "effectiveType": "4g",
            "rtt": _pick(CONNECTION_RTT_VALUES),
            "saveData": False,
            "type": "wifi",
        },
        "pluginsLength": _pick([3, 4, 5]),
    }


def _parse_proxy(value: Optional[str]) -> Optional[Dict[str, str]]:
    if not value:
        return None

    try:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if not parsed.hostname:
            raise ValueError("missing hostname")

        server = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            server = f"{server}:{parsed.port}"

        proxy: Dict[str, str] = {"server": server}
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password

        return proxy
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Invalid proxy '%s': %s", value, exc)
        return None


@dataclass
class PlaywrightConfig:
    headless: bool = True
    args: Optional[List[str]] = None
    proxy: Optional[Dict[str, str]] = None
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    locale: Optional[str] = None
    timezone_id: Optional[str] = None
    device_scale_factor: Optional[float] = None
    color_scheme: Optional[str] = None


DEFAULT_CONFIG = PlaywrightConfig(
    headless=True,
    args=[
        "--unlimited-storage",
        "--full-memory-crash-report",
        "--disable-gpu",
        "--ignore-certificate-errors",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--lang=en-US;q=0.9,en;q=0.8",
    ],
    proxy=_parse_proxy(os.getenv("ODDS_PORTAL_PROXY_URL")),
)


class PlaywrightBrowser:
    """Wrapper that mirrors the Node.js helper but for async Playwright."""

    def __init__(self, config: Optional[Dict[str, object]] = None):
        merged = DEFAULT_CONFIG.__dict__ | (config or {})
        merged.setdefault("user_agent", _pick(USER_AGENTS))
        merged.setdefault("args", list(DEFAULT_CONFIG.args or []))
        merged.setdefault("headless", DEFAULT_CONFIG.headless)

        proxy = merged.get("proxy")
        if isinstance(proxy, str):
            merged["proxy"] = _parse_proxy(proxy)

        self.config = merged
        self._playwright = None
        self._browser: Optional[PwBrowser] = None
        self._contexts: set[BrowserContext] = set()
        self._pages: set[Page] = set()

    async def init(self) -> "PlaywrightBrowser":
        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": bool(self.config.get("headless", True)),
            "args": self.config.get("args"),
            "ignore_default_args": ["--mute-audio"],
        }
        if self.config.get("proxy"):
            launch_args["proxy"] = self.config["proxy"]

        self._browser = await self._playwright.chromium.launch(**launch_args)
        if not self._browser.is_connected():
            await self.cleanup()
            raise RuntimeError("Browser failed to initialize")

        return self

    async def new_page(self) -> Page:
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Browser not initialized")

        viewport = self.config.get("viewport") or _pick(DESKTOP_VIEWPORTS)
        scale_factor = self.config.get("device_scale_factor") or _pick(DEVICE_SCALE_FACTORS)
        timezone = self.config.get("timezone_id") or _pick(TIMEZONE_IDS)
        locale = self.config.get("locale") or _pick(LOCALE_OPTIONS)
        color_scheme = self.config.get("color_scheme") or _pick(COLOR_SCHEMES)

        fingerprint = _build_fingerprint(
            {
                "user_agent": self.config.get("user_agent"),
                "locale": locale,
                "viewport": viewport,
                "color_scheme": color_scheme,
            }
        )

        context = await self._browser.new_context(
            user_agent=self.config.get("user_agent"),
            ignore_https_errors=True,
            viewport=viewport,
            screen={"width": viewport["width"], "height": viewport["height"]},
            locale=locale,
            timezone_id=timezone,
            color_scheme=color_scheme,
            device_scale_factor=scale_factor,
            is_mobile=False,
            has_touch=fingerprint["maxTouchPoints"] > 0,
        )
        self._contexts.add(context)

        await context.set_extra_http_headers({"Accept-Language": fingerprint["acceptLanguage"]})

        page = await context.new_page()
        self._pages.add(page)

        await page.emulate_media(color_scheme=color_scheme)
        await self._configure_page(page, fingerprint | {"devicePixelRatio": scale_factor})
        await page.set_viewport_size(viewport)
        return page

    async def _configure_page(self, page: Page, fingerprint: Dict[str, object]) -> None:
        fingerprint_json = json.dumps(fingerprint)
        script_template = """
        (() => {
            const fingerprint = __FINGERPRINT__;
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                localStorage.setItem('isTeamPageModalClosed', 'true');

                const definedPlugins = Array.from({ length: fingerprint.pluginsLength }, (_, idx) => idx + 1);
                Object.defineProperty(navigator, 'plugins', { get: () => definedPlugins });
                Object.defineProperty(navigator, 'languages', { get: () => fingerprint.languages });
                Object.defineProperty(navigator, 'language', { get: () => fingerprint.languages[0] });
                Object.defineProperty(navigator, 'maxTouchPoints', { get: () => fingerprint.maxTouchPoints });
                Object.defineProperty(navigator, 'vendor', { get: () => fingerprint.navigator.vendor });
                Object.defineProperty(navigator, 'appVersion', { get: () => fingerprint.navigator.appVersion });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => fingerprint.hardwareConcurrency });
                Object.defineProperty(navigator, 'platform', { get: () => fingerprint.navigator.platform });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => fingerprint.deviceMemory });
                Object.defineProperty(window, 'devicePixelRatio', { get: () => fingerprint.devicePixelRatio });
                Object.defineProperty(navigator, 'connection', { configurable: true, get: () => fingerprint.connection });

                if (window.screen) {
                    Object.defineProperty(window.screen, 'width', { get: () => fingerprint.screen.width });
                    Object.defineProperty(window.screen, 'height', { get: () => fingerprint.screen.height });
                    Object.defineProperty(window.screen, 'availWidth', { get: () => fingerprint.screen.availWidth });
                    Object.defineProperty(window.screen, 'availHeight', { get: () => fingerprint.screen.availHeight });
                    Object.defineProperty(window.screen, 'colorDepth', { get: () => fingerprint.screen.colorDepth });
                    Object.defineProperty(window.screen, 'pixelDepth', { get: () => fingerprint.screen.pixelDepth });
                }

                try {
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function (parameter) {
                        if (parameter === 37445) {
                            return 'Google Inc. (Intel)';
                        }
                        if (parameter === 37446) {
                            return 'ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        }
                        return getParameter.call(this, parameter);
                    };
                } catch (error) {
                    console.warn('WebGL override skipped', error);
                }

                if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                    navigator.mediaDevices.getUserMedia = function (constraints) {
                        if (constraints && constraints.video) {
                            return Promise.resolve({
                                getTracks: () => [],
                                getVideoTracks: () => [],
                                getAudioTracks: () => [],
                                getTrackById: () => null,
                                addTrack: () => {},
                                removeTrack: () => {},
                                stop: () => {},
                            });
                        }
                        return originalGetUserMedia(constraints);
                    };
                }

                if (navigator.permissions && navigator.permissions.query) {
                    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
                    navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications'
                            ? Promise.resolve({ state: Notification.permission })
                            : originalQuery(parameters)
                    );
                }
        })();
        """
        script = script_template.replace("__FINGERPRINT__", fingerprint_json)
        await page.add_init_script(script=script)

    async def close(self) -> None:
        for page in list(self._pages):
            try:
                if not page.is_closed():
                    await page.close()
            finally:
                self._pages.discard(page)

        for context in list(self._contexts):
            try:
                await context.close()
            finally:
                self._contexts.discard(context)

        if self._browser and self._browser.is_connected():
            await self._browser.close()
        self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def cleanup(self) -> None:
        await self.close()


async def launch_browser(config: Optional[Dict[str, object]] = None) -> PlaywrightBrowser:
    browser = PlaywrightBrowser(config)
    await browser.init()
    return browser


__all__ = ["launch_browser", "PlaywrightBrowser"]
