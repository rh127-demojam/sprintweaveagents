"""CPAT application version: YY.M.W (year.month.week-of-month).

Format (image tags, env, API):
  YY — two-digit calendar year
  M  — calendar month without leading zero for 1–9 (e.g. 7); 10–12 unchanged
  W  — week of the month (1–5), where days 1–7 are week 1, 8–14 week 2, etc.

The UI prefixes this with ``v`` for display (vYY.M.W) only.

Override with environment variable ``CPAT_VERSION`` (e.g. for pinned image builds).
"""

from __future__ import annotations

import os
from datetime import date, datetime


def week_of_month(day: int) -> int:
    """Return 1–5 for calendar day-of-month (1–7 → 1, 8–14 → 2, …)."""
    if day < 1 or day > 31:
        raise ValueError(f"Invalid day of month: {day}")
    return ((day - 1) // 7) + 1


def format_cpat_version(when: date | datetime | None = None) -> str:
    """Return CPAT version string ``YY.M.W`` for the given (or current) date."""
    if when is None:
        when = date.today()
    elif isinstance(when, datetime):
        when = when.date()

    yy = when.year % 100
    m = when.month
    w = week_of_month(when.day)
    return f"{yy:02d}.{m}.{w}"


def normalize_cpat_version(value: str) -> str:
    """Normalize to ``YY.M.W`` (strip optional leading ``v``)."""
    cleaned = value.strip().lstrip("vV")
    return cleaned if cleaned else format_cpat_version()


def resolve_cpat_version(when: date | datetime | None = None) -> str:
    """Prefer ``CPAT_VERSION`` env override; otherwise compute ``YY.M.W``."""
    override = (os.environ.get("CPAT_VERSION") or "").strip()
    if override:
        return normalize_cpat_version(override)
    return format_cpat_version(when)


APP_VERSION = os.environ.get("CPAT_VERSION", "25.10.1")
