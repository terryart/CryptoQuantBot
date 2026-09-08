# CryptoQuantBot

A small, deterministic Python project for researching a crypto trading idea with **historical backtesting instead of live execution**.

The current strategy is intentionally simple: a fast/slow moving-average crossover with configurable fees, position sizing, and an optional stop-loss. The useful part is the engineering around it: explicit assumptions, no-lookahead signal generation, deterministic results, input validation, and tests.

## Features

- Uses only information available before each simulated bar
- Includes configurable trading fees
- Bounded position sizing and optional stop-loss
- Reports return, trade count, and maximum drawdown
- Ships with deterministic sample data
- Uses Python's standard library only
- Has a small unit-test suite
- Deliberately has no exchange-key or live-order path

## Quick start

Requires Python 3.11+.

```bash
python cryptoquantbot.py --csv sample_prices.csv
```

Custom run:

```bash
python cryptoquantbot.py --csv sample_prices.csv --fast 5 --slow 20 --cash 10000 --fee-bps 10
```

## Tests

```bash
python -m unittest -v test_cryptoquantbot.py
```

## CSV format

```csv
date,close
2026-01-01,100.25
2026-01-02,101.10
```

## Next steps

- walk-forward evaluation
- benchmark/buy-and-hold comparison
- parameter-sensitivity reports
- richer risk and exposure metrics
- strategy interface for multiple models
- CI on every pull request

## Scope

**Educational research software only.** This repository is not investment advice and does not place live orders, store exchange credentials, or connect to an exchange.
