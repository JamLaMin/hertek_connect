from __future__ import annotations

from datetime import datetime, timezone


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v).astimezone(timezone.utc)
    except Exception:
        return None


def upper(v) -> str:
    return str(v or "").upper()
