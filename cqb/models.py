"""Core domain models for CryptoQuantBot."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PriceBar:
    """One market-data bar.

    ``timestamp`` may be an ISO date/time string or an exchange epoch string.
    Only ``close`` is required so legacy close-only datasets remain valid.
    """

    timestamp: str
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None

    @property
    def date(self) -> str:
        """Backward-compatible alias used by the original public prototype."""

        return self.timestamp


@dataclass(frozen=True)
class BacktestConfig:
    starting_cash: float = 10_000.0
    fee_bps: float = 10.0
    slippage_bps: float = 0.0
    position_fraction: float = 0.95
    stop_loss_pct: float | None = 0.08
    take_profit_pct: float | None = None


@dataclass(frozen=True)
class BacktestResult:
    starting_cash: float
    ending_equity: float
    return_pct: float
    trades: int
    max_drawdown_pct: float
    round_trips: int = 0
    win_rate_pct: float = 0.0
    fees_paid: float = 0.0
    exposure_pct: float = 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "starting_cash": round(self.starting_cash, 2),
            "ending_equity": round(self.ending_equity, 2),
            "return_pct": round(self.return_pct, 2),
            "trades": self.trades,
            "round_trips": self.round_trips,
            "win_rate_pct": round(self.win_rate_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "fees_paid": round(self.fees_paid, 4),
            "exposure_pct": round(self.exposure_pct, 2),
        }


@dataclass(frozen=True)
class ParameterScore:
    fast_window: int
    slow_window: int
    return_pct: float
    max_drawdown_pct: float
    trades: int


@dataclass(frozen=True)
class WalkForwardFold:
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    fast_window: int
    slow_window: int
    test_return_pct: float
    test_max_drawdown_pct: float
    ending_equity: float


@dataclass(frozen=True)
class WalkForwardResult:
    starting_cash: float
    ending_equity: float
    return_pct: float
    folds: tuple[WalkForwardFold, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "starting_cash": round(self.starting_cash, 2),
            "ending_equity": round(self.ending_equity, 2),
            "return_pct": round(self.return_pct, 2),
            "folds": [
                {
                    "train": [fold.train_start, fold.train_end],
                    "test": [fold.test_start, fold.test_end],
                    "fast_window": fold.fast_window,
                    "slow_window": fold.slow_window,
                    "test_return_pct": round(fold.test_return_pct, 2),
                    "test_max_drawdown_pct": round(fold.test_max_drawdown_pct, 2),
                    "ending_equity": round(fold.ending_equity, 2),
                }
                for fold in self.folds
            ],
        }
