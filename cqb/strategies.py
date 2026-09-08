"""Strategy interfaces and deterministic reference strategies."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Protocol, Sequence

from .indicators import ema, rsi
from .models import PriceBar


class Strategy(Protocol):
    name: str

    def generate(self, bars: Sequence[PriceBar]) -> list[int]:
        """Return long/flat targets (1 or 0), one per bar."""


@dataclass(frozen=True)
class MovingAverageCrossStrategy:
    fast_window: int = 5
    slow_window: int = 20
    name: str = "ma_cross"

    def __post_init__(self) -> None:
        if self.fast_window <= 0 or self.slow_window <= 0:
            raise ValueError("windows must be positive")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

    def generate(self, bars: Sequence[PriceBar]) -> list[int]:
        closes = [bar.close for bar in bars]
        signals = [0] * len(closes)
        # Signal at i uses data through i-1, so execution at bar i has no lookahead.
        for i in range(self.slow_window, len(closes)):
            fast = fmean(closes[i - self.fast_window : i])
            slow = fmean(closes[i - self.slow_window : i])
            signals[i] = int(fast > slow)
        return signals


@dataclass(frozen=True)
class EMATrendStrategy:
    fast_window: int = 8
    slow_window: int = 21
    name: str = "ema_trend"

    def __post_init__(self) -> None:
        if self.fast_window <= 0 or self.slow_window <= 0:
            raise ValueError("windows must be positive")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

    def generate(self, bars: Sequence[PriceBar]) -> list[int]:
        closes = [bar.close for bar in bars]
        fast = ema(closes, self.fast_window)
        slow = ema(closes, self.slow_window)
        signals = [0] * len(closes)
        for i in range(1, len(closes)):
            previous_fast = fast[i - 1]
            previous_slow = slow[i - 1]
            if previous_fast is not None and previous_slow is not None:
                signals[i] = int(previous_fast > previous_slow)
        return signals


@dataclass(frozen=True)
class RSIMeanReversionStrategy:
    period: int = 14
    entry_rsi: float = 30.0
    exit_rsi: float = 55.0
    name: str = "rsi_mean_reversion"

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")
        if not 0 < self.entry_rsi < self.exit_rsi < 100:
            raise ValueError("require 0 < entry_rsi < exit_rsi < 100")

    def generate(self, bars: Sequence[PriceBar]) -> list[int]:
        closes = [bar.close for bar in bars]
        values = rsi(closes, self.period)
        signals = [0] * len(closes)
        holding = False
        for i in range(1, len(closes)):
            previous = values[i - 1]
            if previous is not None:
                if not holding and previous <= self.entry_rsi:
                    holding = True
                elif holding and previous >= self.exit_rsi:
                    holding = False
            signals[i] = int(holding)
        return signals


def generate_ma_signals(
    closes: Sequence[float], fast_window: int = 5, slow_window: int = 20
) -> list[int]:
    bars = [PriceBar(str(i), float(close)) for i, close in enumerate(closes)]
    return MovingAverageCrossStrategy(fast_window, slow_window).generate(bars)
