"""Resolve all unique match links from a list page."""

from __future__ import annotations

import os
from typing import List, TypedDict

from playwright.async_api import Page

from ...logger import logger

MATCH_ROW_SELECTOR = 'div[data-testid="game-row"]'
DEBUG_SECTIONS_ENV = "ODDS_PORTAL_DEBUG_SECTIONS"


class MatchItem(TypedDict):
    link: str
    section: str | None


def _dedupe_links(seq: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _dedupe_items(seq: List[MatchItem]) -> List[MatchItem]:
    seen: dict[str, MatchItem] = {}
    result: List[MatchItem] = []
    for item in seq:
        link = item.get("link")
        if not link:
            continue
        existing = seen.get(link)
        if existing:
            if not existing.get("section") and item.get("section"):
                existing["section"] = item["section"]
            continue
        seen[link] = item
        result.append(item)
    return result


async def collect_match_items(
    page: Page,
    limit: int | None = None,
    league_name: str | None = None,
) -> List[MatchItem]:
    logger.info("fetching match links")
    debug_sections = os.getenv(DEBUG_SECTIONS_ENV, "").strip().lower() in {"1", "true", "yes", "on"}
    await page.wait_for_selector(MATCH_ROW_SELECTOR)
    result = await page.evaluate(
        r"""
        ({ matchSelector, leagueName, debugSections }) => {
            const rows = Array.from(document.querySelectorAll(matchSelector));
            if (!rows.length) {
                return debugSections ? { items: [], debug: {} } : [];
            }

            const headerHints = [
                "group",
                "category",
                "stage",
                "round",
                "section",
                "phase",
                "header",
                "title",
                "label",
                "name",
            ];
            const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun", "yesterday", "today", "tomorrow"];
            const monthPattern = /(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)/i;
            const dateNumericPattern = /\b\d{1,4}[./-]\d{1,2}(?:[./-]\d{1,4})?\b/;
            const yearSpanPattern = /\b\d{4}\s*[/-]\s*\d{2,4}\b/;
            const timePattern = /\b\d{1,2}:\d{2}\b/;
            const headerKeywordAllowsDigits = /(round|stage|week|series|matchday|day|leg)/i;
            const stageKeywordPattern = /(pre[- ]?season|regular season|play[- ]?offs?|play[- ]?in|finals?|in[- ]?season)/i;
            const ignoredSections = new Set([
                "basketball",
                "football",
                "soccer",
                "tennis",
                "ice hockey",
                "hockey",
                "baseball",
                "handball",
                "volleyball",
                "rugby",
                "cricket",
                "darts",
                "snooker",
                "futsal",
                "floorball",
                "esports",
                "mma",
                "boxing",
            ]);
            const leagueTokens = (leagueName || "")
                .split(/[^a-z0-9]+/i)
                .map((token) => token.toLowerCase())
                .filter(Boolean);
            for (const token of leagueTokens) {
                ignoredSections.add(token);
            }

            const listRootBase = (() => {
                if (rows.length === 1) {
                    return rows[0].parentElement || rows[0];
                }
                const ancestors = new Set();
                let node = rows[0];
                while (node) {
                    ancestors.add(node);
                    node = node.parentElement;
                }
                let cursor = rows[rows.length - 1];
                while (cursor && !ancestors.has(cursor)) {
                    cursor = cursor.parentElement;
                }
                return cursor || rows[0].parentElement || rows[0];
            })();

            const normalize = (text) => text.replace(/\s+/g, " ").trim();
            const looksLikeDate = (text) => {
                if (!text) return true;
                const lower = text.toLowerCase();
                if (days.some((day) => lower.includes(day))) return true;
                if (monthPattern.test(text)) return true;
                if (dateNumericPattern.test(text)) return true;
                if (yearSpanPattern.test(text)) return true;
                if (timePattern.test(text)) return true;
                return false;
            };

            const isHeaderText = (text) => {
                if (!text) return false;
                if (text.length < 4 || text.length > 40) return false;
                if (looksLikeDate(text)) return false;
                if (!/[A-Za-z]/.test(text)) return false;
                if (/\d/.test(text) && !headerKeywordAllowsDigits.test(text)) return false;
                const normalized = text.toLowerCase();
                if (ignoredSections.has(normalized)) return false;
                return true;
            };

            const extractStageLabel = (text) => {
                if (!text) return null;
                const match = text.match(stageKeywordPattern);
                if (!match) return null;
                const raw = match[0].toLowerCase().replace(/[^a-z]+/g, " ").trim();
                if (/pre\s*season/.test(raw)) return "Pre-season";
                if (/regular\s*season/.test(raw)) return "Regular Season";
                if (/play\s*in/.test(raw)) return "Play In";
                if (/play\s*off/.test(raw)) return "Play Offs";
                if (/in\s*season/.test(raw)) return "In-Season";
                if (/final/.test(raw)) return "Finals";
                return match[0].replace(/\s+/g, " ").trim();
            };

            const normalizeSection = (text) => normalize(text).replace(/\s+/g, " ");
            const isIgnoredSection = (text) => {
                if (!text) return true;
                const normalized = normalizeSection(text).toLowerCase();
                return ignoredSections.has(normalized);
            };

            const isHeaderEl = (el) => {
                if (!el) return false;
                if (el.closest(matchSelector)) return false;
                const text = normalize(el.textContent || "");
                if (!isHeaderText(text)) return false;
                const testId = (el.getAttribute("data-testid") || "").toLowerCase();
                const className = (el.className || "").toString().toLowerCase();
                const role = (el.getAttribute("role") || "").toLowerCase();
                const tag = (el.tagName || "").toLowerCase();
                const hintSource = `${testId} ${className}`;
                const hasHint = headerHints.some((hint) => hintSource.includes(hint));
                if (hasHint) return true;
                if (role === "heading") return true;
                if (["h2", "h3", "h4"].includes(tag)) return true;
                if (el.children.length === 0) return true;
                return false;
            };

            const listRoot = listRootBase;

            const walker = document.createTreeWalker(listRoot, NodeFilter.SHOW_ELEMENT);
            let currentSection = null;
            const results = [];
            const debugHeaders = [];
            const debugRows = [];
            while (walker.nextNode()) {
                const el = walker.currentNode;
                if (el.matches(matchSelector)) {
                    const linkEl = el.matches("a[href]") ? el : el.querySelector("a[href]");
                    if (linkEl) {
                        results.push({ link: linkEl.getAttribute("href"), section: currentSection });
                        continue;
                    }
                    const rowText = normalize(el.textContent || "");
                    const stageLabel = extractStageLabel(rowText);
                    if (stageLabel) {
                        currentSection = isIgnoredSection(stageLabel) ? null : stageLabel;
                    } else if (isHeaderText(rowText)) {
                        currentSection = isIgnoredSection(rowText) ? null : rowText;
                        if (debugSections && currentSection) {
                            debugRows.push({
                                text: currentSection,
                                tag: el.tagName ? el.tagName.toLowerCase() : "",
                                className: (el.className || "").toString().slice(0, 80),
                                testId: el.getAttribute ? el.getAttribute("data-testid") : "",
                            });
                        }
                    }
                    continue;
                }
                if (isHeaderEl(el)) {
                    const headerText = normalize(el.textContent || "");
                    const stageLabel = extractStageLabel(headerText);
                    currentSection = isIgnoredSection(stageLabel || headerText) ? null : (stageLabel || headerText);
                    if (debugSections && currentSection) {
                        debugHeaders.push({
                            text: currentSection,
                            tag: el.tagName ? el.tagName.toLowerCase() : "",
                            className: (el.className || "").toString().slice(0, 80),
                            testId: el.getAttribute ? el.getAttribute("data-testid") : "",
                            role: el.getAttribute ? el.getAttribute("role") : "",
                        });
                    }
                }
            }

            const filtered = results.filter((item) => item.link);
            const hasMeaningfulSection = filtered.some((item) => item.section && !isIgnoredSection(item.section));
            if (!hasMeaningfulSection) {
                let node = listRoot;
                for (let i = 0; i < 3 && node; i += 1) {
                    const candidates = node.querySelectorAll("h1, h2, h3, h4, [role='heading'], [data-testid], [class]");
                    for (const el of candidates) {
                        const text = normalize(el.textContent || "");
                        if (!text || isIgnoredSection(text)) continue;
                        const stageLabel = extractStageLabel(text);
                        if (stageLabel && !isIgnoredSection(stageLabel)) {
                            for (const item of filtered) {
                                item.section = stageLabel;
                            }
                            return filtered;
                        }
                    }
                    node = node.parentElement;
                }
            }

            if (!debugSections) {
                return filtered;
            }

            const stageMatches = [];
            const stageSelectors = ["h1", "h2", "h3", "h4", "[role='heading']", "button", "a", "span", "div"];
            const stageNodes = document.querySelectorAll(stageSelectors.join(","));
            for (const el of stageNodes) {
                if (stageMatches.length >= 25) break;
                const text = normalize(el.textContent || "");
                if (!text || text.length > 60) continue;
                if (!stageKeywordPattern.test(text)) continue;
                const label = extractStageLabel(text);
                stageMatches.push({
                    text,
                    label,
                    tag: el.tagName ? el.tagName.toLowerCase() : "",
                    className: (el.className || "").toString().slice(0, 80),
                    testId: el.getAttribute ? el.getAttribute("data-testid") : "",
                    role: el.getAttribute ? el.getAttribute("role") : "",
                    ariaSelected: el.getAttribute ? el.getAttribute("aria-selected") : "",
                    dataState: el.getAttribute ? el.getAttribute("data-state") : "",
                    dataActive: el.getAttribute ? el.getAttribute("data-active") : "",
                });
            }

            return {
                items: filtered,
                debug: {
                    headers: debugHeaders.slice(0, 25),
                    rowHeaders: debugRows.slice(0, 25),
                    stageMatches,
                },
            };
        }
        """,
        {
            "matchSelector": MATCH_ROW_SELECTOR,
            "leagueName": league_name,
            "debugSections": debug_sections,
        },
    )
    if debug_sections and isinstance(result, dict):
        items = result.get("items", [])
        debug = result.get("debug", {})
        headers = debug.get("headers") or []
        row_headers = debug.get("rowHeaders") or []
        stage_matches = debug.get("stageMatches") or []
        if headers:
            logger.info("Header candidates: %s", ", ".join(item["text"] for item in headers if item.get("text")))
        if row_headers:
            logger.info("Row header candidates: %s", ", ".join(item["text"] for item in row_headers if item.get("text")))
        if stage_matches:
            logger.info("Stage keyword matches: %s", ", ".join(item["text"] for item in stage_matches if item.get("text")))
            stage_labels = [item.get("label") for item in stage_matches if item.get("label")]
            if stage_labels:
                logger.info("Stage labels: %s", ", ".join(dict.fromkeys(stage_labels)))
    else:
        items = result
    unique_items = _dedupe_items(items)
    if isinstance(limit, int):
        return unique_items[:limit]
    if unique_items:
        sections = []
        for item in unique_items:
            section = item.get("section")
            if section and section not in sections:
                sections.append(section)
        if sections:
            logger.info("Detected sections: %s", ", ".join(sections))
    return unique_items


async def collect_match_links(page: Page, limit: int | None = None) -> List[str]:
    items = await collect_match_items(page, limit)
    return _dedupe_links([item["link"] for item in items])


__all__ = ["collect_match_items", "collect_match_links"]
