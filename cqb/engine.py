"""Deterministic long/flat backtesting engine."""
from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .models import BacktestConfig, BacktestResult, PriceBar
from .strategies import Strategy


def max_drawdown(curve: Sequence[float]) -> float:
    if not curve:
        return 0.0
    peak = curve[0]
    worst = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak)
    return abs(worst) * 100.0


def _validate(config: BacktestConfig, bars: Sequence[PriceBar]) -> None:
    if not bars:
        raise ValueError("bars cannot be empty")
    if config.starting_cash <= 0:
        raise ValueError("starting_cash must be positive")
    if config.fee_bps < 0:
        raise ValueError("fee_bps cannot be negative")
    if config.slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative")
    if not 0 < config.position_fraction <= 1:
        raise ValueError("position_fraction must be in (0, 1]")
    if config.stop_loss_pct is not None and not 0 < config.stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    if config.take_profit_pct is not None and config.take_profit_pct <= 0:
        raise ValueError("take_profit_pct must be positive")


def backtest_strategy(
    bars: Sequence[PriceBar],
    strategy: Strategy,
    config: BacktestConfig = BacktestConfig(),
    *,
    start_index: int = 0,
) -> BacktestResult:
    """Backtest a target-position strategy.

    The reference engine is intentionally conservative and simple: long/flat only,
    fills occur at the current bar close plus configurable slippage, and stop/take
    profit checks use close prices. It is a research kernel, not an exchange simulator.
    """

    _validate(config, bars)
    if not 0 <= start_index < len(bars):
        raise ValueError("start_index must point to a bar in the dataset")
    signals = strategy.generate(bars)
    if len(signals) != len(bars):
        raise ValueError("strategy must emit one signal per bar")
    if any(signal not in (0, 1) for signal in signals):
        raise ValueError("reference engine accepts only long/flat signals (0 or 1)")

    fee_rate = config.fee_bps / 10_000.0
    slip_rate = config.slippage_bps / 10_000.0
    cash = config.starting_cash
    units = 0.0
    entry_price: float | None = None
    entry_cost = 0.0
    trades = 0
    round_trips = 0
    wins = 0
    fees_paid = 0.0
    exposure_bars = 0
    curve: list[float] = []

    def close_position(reference_price: float) -> None:
        nonlocal cash, units, entry_price, entry_cost, trades, round_trips, wins, fees_paid
        execution_price = reference_price * (1.0 - slip_rate)
        gross = units * execution_price
        fee = gross * fee_rate
        proceeds = gross - fee
        pnl = proceeds - entry_cost
        cash += proceeds
        fees_paid += fee
        trades += 1
        round_trips += 1
        wins += int(pnl > 0)
        units = 0.0
        entry_price = None
        entry_cost = 0.0

    for index, (bar, signal) in enumerate(zip(bars, signals)):
        if index < start_index:
            continue
        price = bar.close
        stopped = (
            units > 0
            and entry_price is not None
            and config.stop_loss_pct is not None
            and price <= entry_price * (1.0 - config.stop_loss_pct)
        )
        took_profit = (
            units > 0
            and entry_price is not None
            and config.take_profit_pct is not None
            and price >= entry_price * (1.0 + config.take_profit_pct)
        )

        if units > 0 and (signal == 0 or stopped or took_profit):
            close_position(price)

        if units == 0 and signal == 1:
            budget = cash * config.position_fraction
            notional = budget / (1.0 + fee_rate)
            fee = notional * fee_rate
            execution_price = price * (1.0 + slip_rate)
            units = notional / execution_price
            entry_price = execution_price
            entry_cost = notional + fee
            cash -= entry_cost
            fees_paid += fee
            trades += 1

        if units > 0:
            exposure_bars += 1
        curve.append(cash + units * price)

    if units > 0:
        close_position(bars[-1].close)
        curve[-1] = cash

    ending = cash
    return BacktestResult(
        starting_cash=config.starting_cash,
        ending_equity=ending,
        return_pct=(ending / config.starting_cash - 1.0) * 100.0,
        trades=trades,
        max_drawdown_pct=max_drawdown(curve),
        round_trips=round_trips,
        win_rate_pct=(wins / round_trips * 100.0) if round_trips else 0.0,
        fees_paid=fees_paid,
        exposure_pct=exposure_bars / (len(bars) - start_index) * 100.0,
    )


def with_starting_cash(config: BacktestConfig, cash: float) -> BacktestConfig:
    """Return a copy for chained evaluation folds."""

    return replace(config, starting_cash=cash)
