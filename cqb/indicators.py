"""Dependency-free technical indicators used by research strategies."""
from __future__ import annotations

from math import sqrt
from statistics import fmean
from typing import Sequence


def sma(values: Sequence[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) < window:
        return out
    running = sum(values[:window])
    out[window - 1] = running / window
    for i in range(window, len(values)):
        running += values[i] - values[i - window]
        out[i] = running / window
    return out


def ema(values: Sequence[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) < window:
        return out
    seed = fmean(values[:window])
    out[window - 1] = seed
    alpha = 2.0 / (window + 1.0)
    previous = seed
    for i in range(window, len(values)):
        previous = values[i] * alpha + previous * (1.0 - alpha)
        out[i] = previous
    return out


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    """Wilder RSI. The first value appears at index ``period``."""

    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = fmean(gains)
    avg_loss = fmean(losses)

    def value(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        rs = gain / loss
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = value(avg_gain, avg_loss)
    return out


def bollinger_bands(
    values: Sequence[float], window: int = 20, deviations: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    if window <= 1:
        raise ValueError("window must be greater than 1")
    if deviations <= 0:
        raise ValueError("deviations must be positive")

    middle: list[float | None] = [None] * len(values)
    upper: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    for i in range(window - 1, len(values)):
        sample = values[i - window + 1 : i + 1]
        mean = fmean(sample)
        variance = sum((x - mean) ** 2 for x in sample) / window
        std = sqrt(variance)
        middle[i] = mean
        upper[i] = mean + deviations * std
        lower[i] = mean - deviations * std
    return middle, upper, lower
