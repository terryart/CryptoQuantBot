"""CSV loading and serialization."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

from .models import PriceBar


def _optional_float(raw: str | None, name: str, *, positive: bool = True) -> float | None:
    if raw is None or raw == "":
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if not positive and value < 0:
        raise ValueError(f"{name} cannot be negative")
    return value


def load_prices(path: str | Path) -> list[PriceBar]:
    """Load close-only or OHLCV market data from CSV.

    Required columns: ``close`` and either ``date`` or ``timestamp``.
    Optional columns: ``open``, ``high``, ``low``, ``volume``.
    """

    rows: list[PriceBar] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        time_column = "timestamp" if "timestamp" in fields else "date" if "date" in fields else None
        if time_column is None or "close" not in fields:
            raise ValueError("CSV must contain close and either date or timestamp columns")

        for raw in reader:
            timestamp = (raw.get(time_column) or "").strip()
            if not timestamp:
                raise ValueError("timestamp/date cannot be empty")
            close = _optional_float(raw.get("close"), "close")
            if close is None:
                raise ValueError("close cannot be empty")
            rows.append(
                PriceBar(
                    timestamp=timestamp,
                    close=close,
                    open=_optional_float(raw.get("open"), "open"),
                    high=_optional_float(raw.get("high"), "high"),
                    low=_optional_float(raw.get("low"), "low"),
                    volume=_optional_float(raw.get("volume"), "volume", positive=False),
                )
            )

    if not rows:
        raise ValueError("CSV contains no price rows")
    return rows


def write_prices(path: str | Path, bars: Iterable[PriceBar]) -> None:
    """Write bars in a stable OHLCV-friendly CSV format."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "timestamp": bar.timestamp,
                    "open": "" if bar.open is None else bar.open,
                    "high": "" if bar.high is None else bar.high,
                    "low": "" if bar.low is None else bar.low,
                    "close": bar.close,
                    "volume": "" if bar.volume is None else bar.volume,
                }
            )
