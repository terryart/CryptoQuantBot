"""Parameter sensitivity, benchmarks, and walk-forward evaluation."""
from __future__ import annotations

from dataclasses import replace
from itertools import product
from typing import Iterable, Sequence

from .engine import backtest_strategy
from .models import (
    BacktestConfig,
    BacktestResult,
    ParameterScore,
    PriceBar,
    WalkForwardFold,
    WalkForwardResult,
)
from .strategies import MovingAverageCrossStrategy


class _AlwaysLong:
    name = "buy_and_hold"

    def generate(self, bars: Sequence[PriceBar]) -> list[int]:
        return [1] * len(bars)


def buy_and_hold(
    bars: Sequence[PriceBar], config: BacktestConfig = BacktestConfig()
) -> BacktestResult:
    """Benchmark the same engine against a first-bar long held to the end."""

    benchmark_config = replace(config, position_fraction=1.0, stop_loss_pct=None, take_profit_pct=None)
    return backtest_strategy(bars, _AlwaysLong(), benchmark_config)


def parameter_sensitivity(
    bars: Sequence[PriceBar],
    fast_windows: Iterable[int],
    slow_windows: Iterable[int],
    config: BacktestConfig = BacktestConfig(),
) -> list[ParameterScore]:
    """Evaluate a moving-average grid and rank return first, drawdown second."""

    scores: list[ParameterScore] = []
    for fast, slow in product(fast_windows, slow_windows):
        if fast <= 0 or slow <= 0 or fast >= slow or slow >= len(bars):
            continue
        result = backtest_strategy(bars, MovingAverageCrossStrategy(fast, slow), config)
        scores.append(
            ParameterScore(
                fast_window=fast,
                slow_window=slow,
                return_pct=result.return_pct,
                max_drawdown_pct=result.max_drawdown_pct,
                trades=result.trades,
            )
        )
    if not scores:
        raise ValueError("parameter grid produced no valid fast/slow combinations")
    return sorted(scores, key=lambda item: (-item.return_pct, item.max_drawdown_pct, item.trades))


def walk_forward(
    bars: Sequence[PriceBar],
    *,
    train_size: int,
    test_size: int,
    fast_windows: Iterable[int],
    slow_windows: Iterable[int],
    config: BacktestConfig = BacktestConfig(),
) -> WalkForwardResult:
    """Repeatedly select parameters on past data, then evaluate on unseen data.

    Each test fold receives only the trailing training bars required to warm up the
    selected moving-average windows. No test observation participates in selection.
    Equity is chained from fold to fold.
    """

    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    if len(bars) <= train_size:
        raise ValueError("not enough bars for a training window plus test data")

    fast_values = tuple(fast_windows)
    slow_values = tuple(slow_windows)
    if not fast_values or not slow_values:
        raise ValueError("parameter grids cannot be empty")

    folds: list[WalkForwardFold] = []
    cash = config.starting_cash
    start = 0
    while start + train_size < len(bars):
        train_end = start + train_size
        test_end = min(train_end + test_size, len(bars))
        train = bars[start:train_end]
        test = bars[train_end:test_end]
        if not test:
            break

        ranking = parameter_sensitivity(train, fast_values, slow_values, replace(config, starting_cash=cash))
        best = ranking[0]
        warmup = train[-best.slow_window :]
        context = list(warmup) + list(test)
        fold_config = replace(config, starting_cash=cash)
        result = backtest_strategy(
            context,
            MovingAverageCrossStrategy(best.fast_window, best.slow_window),
            fold_config,
            start_index=len(warmup),
        )
        cash = result.ending_equity
        folds.append(
            WalkForwardFold(
                train_start=start,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
                fast_window=best.fast_window,
                slow_window=best.slow_window,
                test_return_pct=result.return_pct,
                test_max_drawdown_pct=result.max_drawdown_pct,
                ending_equity=result.ending_equity,
            )
        )
        start += test_size

    return WalkForwardResult(
        starting_cash=config.starting_cash,
        ending_equity=cash,
        return_pct=(cash / config.starting_cash - 1.0) * 100.0,
        folds=tuple(folds),
    )
