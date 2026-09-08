# CryptoQuantBot â€” Development Status

Updated: 2026-09-08

## Current direction

The public GitHub rebuild is now the clean research kernel. The earlier TERRY-PC / USB bot should be treated as a source to audit and merge into this architecture, not as a replacement by default.

## Baseline preserved

Pre-v0.2 backup:

`C:\Users\enoba\CheyWorkspace\Projects\CryptoQuantBot-Public_backup_20260908_031318`

## Current v0.2 implementation

- `cryptoquantbot.py` â€” CLI + backward-compatible facade
- `cqb/models.py` â€” bars/config/results/evaluation models
- `cqb/data.py` â€” close-only + OHLCV CSV IO
- `cqb/indicators.py` â€” SMA, EMA, RSI, Bollinger Bands
- `cqb/strategies.py` â€” MA cross, EMA trend, RSI mean reversion
- `cqb/engine.py` â€” deterministic long/flat simulator with fees, slippage, position fraction, stop loss, take profit, drawdown/exposure/fees/win-rate metrics
- `cqb/evaluation.py` â€” buy-and-hold benchmark, parameter sensitivity, walk-forward evaluation
- `cqb/bybit.py` â€” public Bybit V5 kline adapter only; testnet default; no credentials/order path
- `test_cryptoquantbot.py` â€” 16 deterministic tests
- `.github/workflows/tests.yml` â€” Python 3.11/3.12/3.13 CI
- `SECURITY.md` â€” public/private execution and credential boundary
- `pyproject.toml` â€” v0.2 package metadata

## Verification completed

`python -m unittest -v test_cryptoquantbot.py`

Result: **16/16 PASS**.

Legacy CLI still works:

`python cryptoquantbot.py --csv sample_prices.csv`

Public Bybit testnet fetch also works without an API key. Verified with BTCUSDT 1h candles, including a 500-bar download.

## Research sanity check

Using the 500 most recent BTCUSDT 1h candles returned by Bybit testnet at the time of this checkpoint, 2 bps slippage, and the current reference engine:

- default MA 5/20: +2.53%, max drawdown 17.50%
- buy-and-hold benchmark: +20.20%, max drawdown 8.45%
- best searched in-sample MA grid result: +15.46% (8/20), max drawdown 8.39%
- walk-forward chained result: **-1.71%**

This is useful, not disappointing: the walk-forward layer immediately demonstrated that a strong-looking parameter search does not automatically survive unseen data. Do not treat any of these short-window testnet results as evidence of a trading edge.

Downloaded market data lives under `data/` and is ignored by Git.

## Pending USB merge

Terry will plug in a USB containing:

1. the earlier crypto bot from the TERRY PC;
2. the wallpaper project/assets.

When the USB arrives:

- identify the removable-drive letter;
- inventory both projects before moving anything;
- copy them into a deliberate workspace location on this PC;
- scan the old bot for `.env`, API keys/secrets, logs, account identifiers, cached responses, and other material that must never reach GitHub;
- compare the old bot against the v0.2 public architecture;
- salvage the furthest-working Bybit testnet ingestion/execution, multi-symbol support, logging, risk logic, and any stronger strategy/research work;
- adapt useful pieces behind clean interfaces rather than blindly overwriting the rebuild;
- run regression tests after each merge stage;
- keep authenticated/testnet execution separated from the public research kernel until its safety properties are understood;
- only then decide what is suitable to publish.

## Known earlier bot history to look for

The earlier project used Bybit USDT perpetuals / linear futures and had working testnet connectivity through `pybit.unified_trading.HTTP`. BTCUSDT ticker polling worked and a loop logged prices under `data/YYYYMMDD.csv` plus logs. The older intended architecture included multi-symbol data, strategies, order execution/status, risk management, backtesting, monitoring/alerts, and indicators such as RSI, moving averages/EMA, and Bollinger Bands.

Symbols previously discussed for the bot included BTC, ETH, XRP, XLM, HBAR, XDC, ALGO, IOTA, and ADA.

## Next engineering stage after USB audit

Target: **paper/testnet execution layer with evidence**, not a jump straight to mainnet.

Priority order:

1. adapter boundary between research engine and exchange;
2. authenticated Bybit testnet market/account client from recovered code if sound;
3. typed order lifecycle and reconciliation;
4. idempotency / duplicate-order protection;
5. risk ceilings and kill conditions;
6. structured audit logs;
7. retry/stale-data/disconnect/partial-fill testing;
8. multi-symbol evaluation and regime testing;
9. only after the above, separately gated live execution.

## GitHub

Repo: `terryart/CryptoQuantBot`

Repository description/topics were already polished. Visibility is now explicitly verified in GitHub Settings as **public**.

