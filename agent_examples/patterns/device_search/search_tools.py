"""DuckDuckGo-backed search tools.

All functions return plain dicts so they can be used from workflow nodes
without importing duckduckgo_search at the module level (fail-safe import).
Rate-limiting is handled by catching exceptions and returning partial results.
"""
from __future__ import annotations

import time

_DDGS_AVAILABLE: bool | None = None


def _get_ddgs():  # type: ignore[return]
    global _DDGS_AVAILABLE
    try:
        from ddgs import DDGS  # noqa: PLC0415

        _DDGS_AVAILABLE = True
        return DDGS
    except ImportError:
        _DDGS_AVAILABLE = False
        return None


def _search(query: str, max_results: int = 5, delay: float = 1.0) -> list[dict]:
    """Core DuckDuckGo text search with graceful degradation."""
    DDGS = _get_ddgs()
    if DDGS is None:
        return []
    time.sleep(delay)
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]
    except Exception:
        return []


# ── Domain-specific search helpers ────────────────────────────────────────────


def search_marketplace_listings(
    device_type_en: str,
    device_type_ru: str,
    budget_rub: int | None,
    criteria_hints: list[str] | None = None,
) -> tuple[list[dict], list[str]]:
    """Search for device listings and return (results, queries_used).

    Uses criteria hints to target devices matching user requirements, and
    explicitly queries Russian tech review sites that list specific models.
    """
    budget = f"до {budget_rub} рублей" if budget_rub else ""
    hints_str = " ".join(criteria_hints[:2]) if criteria_hints else ""

    queries = [
        # Criteria-aware: finds review articles that compare devices on the specs we care about
        f"{device_type_ru} {hints_str} {budget} купить 2024 2025".strip(),
        # ixbt.com — лучший русскоязычный источник рейтингов с конкретными моделями
        f"ixbt {device_type_ru} {budget} лучший выбор 2025",
        # 4pda — форум с реальными рекомендациями и сравнениями
        f"4pda посоветуйте {device_type_ru} {budget} рекомендую",
        # Агрегаторы типа ichip, expertcenter
        f"{device_type_ru} {budget} топ рейтинг 2025 ichip expertcenter",
        # Английский поиск по GSMArena/Notebookcheck для актуальных моделей
        f"best {device_type_en} {budget_rub} rubles 2025 gsmarena notebookcheck review",
    ]

    results: list[dict] = []
    for q in queries:
        results.extend(_search(q, max_results=8))

    deduped = _dedupe(results)
    return deduped, queries


def search_device_benchmarks(device_name: str, criterion_hint: str) -> list[dict]:
    """Search benchmarks and expert reviews for a specific device + criterion."""
    queries = [
        f"{device_name} {criterion_hint} review benchmark gsmarena notebookcheck",
        f"{device_name} {criterion_hint} тест обзор характеристики",
        f'"{device_name}" specs display battery performance',
    ]
    results: list[dict] = []
    for q in queries:
        results.extend(_search(q, max_results=4))
    return _dedupe(results)


def search_user_reviews(device_name: str) -> list[dict]:
    """Search user reviews on marketplaces and review aggregators."""
    queries = [
        f"{device_name} отзывы покупателей плюсы минусы",
        f"{device_name} user reviews real experience pros cons",
        f"{device_name} site:otzovik.com OR site:irecommend.ru OR site:market.yandex.ru",
    ]
    results: list[dict] = []
    for q in queries:
        results.extend(_search(q, max_results=4))
    return _dedupe(results)


# ── Utility ───────────────────────────────────────────────────────────────────


def _dedupe(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in results:
        key = r.get("url") or r.get("title", "")
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def format_results_for_llm(results: list[dict], max_chars: int = 4000) -> str:
    """Collapse search results into a text block suitable for an LLM prompt."""
    lines: list[str] = []
    total = 0
    for i, r in enumerate(results, 1):
        block = f"[{i}] {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('snippet', '')}\n"
        if total + len(block) > max_chars:
            break
        lines.append(block)
        total += len(block)
    return "\n".join(lines) if lines else "Результаты не найдены."
