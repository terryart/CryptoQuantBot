"""CryptoQuantBot public research CLI and backward-compatible facade.

The public project deliberately supports research/backtesting and public market-data
collection only. It does not place orders or load exchange credentials.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from cqb import (
    BacktestConfig,
    BacktestResult,
    EMATrendStrategy,
    MovingAverageCrossStrategy,
    PriceBar,
    RSIMeanReversionStrategy,
    backtest_strategy,
    buy_and_hold,
    fetch_bybit_klines,
    generate_ma_signals,
    load_prices,
    parameter_sensitivity,
    walk_forward,
    write_prices,
)


def generate_signals(
    closes: Sequence[float], fast_window: int = 5, slow_window: int = 20
) -> list[int]:
    """Backward-compatible moving-average signal helper."""

    return generate_ma_signals(closes, fast_window, slow_window)


def backtest(
    bars: Sequence[PriceBar],
    *,
    fast_window: int = 5,
    slow_window: int = 20,
    starting_cash: float = 10_000.0,
    fee_bps: float = 10.0,
    position_fraction: float = 0.95,
    stop_loss_pct: float | None = 0.08,
    slippage_bps: float = 0.0,
    take_profit_pct: float | None = None,
) -> BacktestResult:
    """Backward-compatible MA-crossover backtest entrypoint."""

    config = BacktestConfig(
        starting_cash=starting_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        position_fraction=position_fraction,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
    )
    return backtest_strategy(
        bars,
        MovingAverageCrossStrategy(fast_window, slow_window),
        config,
    )


def _csv_ints(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one integer")
    return values


def _config(args: argparse.Namespace) -> BacktestConfig:
    stop = None if getattr(args, "no_stop", False) else args.stop_loss
    return BacktestConfig(
        starting_cash=args.cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        position_fraction=args.position_fraction,
        stop_loss_pct=stop,
        take_profit_pct=args.take_profit,
    )


def _add_engine_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cash", type=float, default=10_000.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--position-fraction", type=float, default=0.95)
    parser.add_argument("--stop-loss", type=float, default=0.08)
    parser.add_argument("--no-stop", action="store_true")
    parser.add_argument("--take-profit", type=float, default=None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crypto strategy research, backtesting, and public market-data collection."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    back = sub.add_parser("backtest", help="run a deterministic historical backtest")
    back.add_argument("--csv", default="sample_prices.csv")
    back.add_argument("--strategy", choices=("ma", "ema", "rsi"), default="ma")
    back.add_argument("--fast", type=int, default=5)
    back.add_argument("--slow", type=int, default=20)
    back.add_argument("--rsi-period", type=int, default=14)
    back.add_argument("--rsi-entry", type=float, default=30.0)
    back.add_argument("--rsi-exit", type=float, default=55.0)
    back.add_argument("--benchmark", action="store_true")
    _add_engine_args(back)

    grid = sub.add_parser("grid", help="rank MA parameter combinations")
    grid.add_argument("--csv", default="sample_prices.csv")
    grid.add_argument("--fast-grid", type=_csv_ints, default=(3, 5, 8, 10))
    grid.add_argument("--slow-grid", type=_csv_ints, default=(15, 20, 30, 50))
    grid.add_argument("--top", type=int, default=10)
    _add_engine_args(grid)

    walk = sub.add_parser("walk-forward", help="select on past data, test on unseen folds")
    walk.add_argument("--csv", default="sample_prices.csv")
    walk.add_argument("--train-size", type=int, default=80)
    walk.add_argument("--test-size", type=int, default=20)
    walk.add_argument("--fast-grid", type=_csv_ints, default=(3, 5, 8, 10))
    walk.add_argument("--slow-grid", type=_csv_ints, default=(15, 20, 30, 50))
    _add_engine_args(walk)

    fetch = sub.add_parser("fetch", help="download public Bybit candles (no API key)")
    fetch.add_argument("symbol")
    fetch.add_argument("--interval", default="60")
    fetch.add_argument("--limit", type=int, default=200)
    fetch.add_argument("--category", choices=("linear", "spot", "inverse"), default="linear")
    fetch.add_argument("--mainnet", action="store_true", help="use public mainnet market data")
    fetch.add_argument("--output", default=None)
    return parser


def _strategy(args: argparse.Namespace):
    if args.strategy == "ma":
        return MovingAverageCrossStrategy(args.fast, args.slow)
    if args.strategy == "ema":
        return EMATrendStrategy(args.fast, args.slow)
    return RSIMeanReversionStrategy(args.rsi_period, args.rsi_entry, args.rsi_exit)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    commands = {"backtest", "grid", "walk-forward", "fetch"}
    # Preserve the original `python cryptoquantbot.py --csv ...` interface.
    if not raw or raw[0] not in commands:
        raw.insert(0, "backtest")

    args = _build_parser().parse_args(raw)

    if args.command == "fetch":
        bars = fetch_bybit_klines(
            args.symbol,
            interval=args.interval,
            limit=args.limit,
            category=args.category,
            testnet=not args.mainnet,
        )
        output = args.output or f"data/{args.symbol.upper()}_{args.interval}.csv"
        write_prices(output, bars)
        print(
            json.dumps(
                {
                    "symbol": args.symbol.upper(),
                    "bars": len(bars),
                    "first": bars[0].timestamp,
                    "last": bars[-1].timestamp,
                    "output": output,
                    "source": "bybit-mainnet-public" if args.mainnet else "bybit-testnet-public",
                },
                indent=2,
            )
        )
        return 0

    bars = load_prices(args.csv)
    config = _config(args)

    if args.command == "backtest":
        result = backtest_strategy(bars, _strategy(args), config)
        payload: dict[str, object] = {"strategy": _strategy(args).name, **result.as_dict()}
        if args.benchmark:
            payload["buy_and_hold"] = buy_and_hold(bars, config).as_dict()
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "grid":
        ranking = parameter_sensitivity(bars, args.fast_grid, args.slow_grid, config)
        print(
            json.dumps(
                [
                    {
                        "fast": item.fast_window,
                        "slow": item.slow_window,
                        "return_pct": round(item.return_pct, 2),
                        "max_drawdown_pct": round(item.max_drawdown_pct, 2),
                        "trades": item.trades,
                    }
                    for item in ranking[: max(args.top, 0)]
                ],
                indent=2,
            )
        )
        return 0

    result = walk_forward(
        bars,
        train_size=args.train_size,
        test_size=args.test_size,
        fast_windows=args.fast_grid,
        slow_windows=args.slow_grid,
        config=config,
    )
    print(json.dumps(result.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
