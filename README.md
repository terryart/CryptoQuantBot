# CryptoQuantBot

A deterministic Python research engine for testing crypto trading hypotheses before they are allowed anywhere near live execution.

CryptoQuantBot started as an automated-trading experiment. The public version is being rebuilt around a stricter idea: **research first, testnet second, live execution only after the evidence and engineering justify it**.

The repository currently supports historical backtesting, multiple reference strategies, realistic friction assumptions, parameter-sensitivity analysis, walk-forward evaluation, and public Bybit candle collection without API credentials.

> Educational/research software only. Nothing in this repository is investment advice or a claim of profitability.

## What is implemented

- Deterministic, no-lookahead backtesting
- Moving-average, EMA-trend, and RSI mean-reversion strategy interfaces
- SMA, EMA, RSI, and Bollinger Band indicators
- Trading fees and configurable slippage
- Position sizing, stop-loss, and take-profit controls
- Return, drawdown, exposure, fees, round trips, and win-rate reporting
- Buy-and-hold benchmark using the same execution engine
- MA parameter-grid / sensitivity analysis
- Walk-forward parameter selection and out-of-sample evaluation
- Close-only and OHLCV CSV support
- Public Bybit V5 kline ingestion (testnet by default, no credentials)
- Unit tests and GitHub Actions CI
- Local paper-execution contract with idempotent client order IDs and hard risk rejection
- No authenticated exchange client and no order-placement path in the public build

## Why walk-forward testing matters

A strategy can look excellent after searching parameters on the same data it is judged on. That is exactly how overfitting hides.

CryptoQuantBot separates parameter selection from later test folds. A parameter set is chosen using past data, then evaluated on unseen data. Strong in-sample performance can therefore fail visibly instead of being mistaken for evidence of an edge.

## Quick start

Requires Python 3.11+ and uses only the standard library.

```bash
python cryptoquantbot.py --csv sample_prices.csv
```

The original CLI remains supported. The explicit equivalent is:

```bash
python cryptoquantbot.py backtest --csv sample_prices.csv
```

Run with a buy-and-hold benchmark:

```bash
python cryptoquantbot.py backtest --csv sample_prices.csv --benchmark --slippage-bps 2
```

Try another reference strategy:

```bash
python cryptoquantbot.py backtest --csv sample_prices.csv --strategy ema --fast 8 --slow 21
python cryptoquantbot.py backtest --csv sample_prices.csv --strategy rsi --rsi-period 14 --rsi-entry 30 --rsi-exit 55
```

## Parameter sensitivity

```bash
python cryptoquantbot.py grid \
  --csv sample_prices.csv \
  --fast-grid 3,5,8,10,12 \
  --slow-grid 15,20,30,40,50 \
  --top 10
```

A best grid result is **not** treated as proof. Use walk-forward evaluation next.

## Walk-forward evaluation

```bash
python cryptoquantbot.py walk-forward \
  --csv sample_prices.csv \
  --train-size 60 \
  --test-size 20 \
  --fast-grid 3,5,8 \
  --slow-grid 15,20,30
```

Each fold selects parameters only from its training window and then evaluates them on later unseen bars.

## Fetch public Bybit candles

Testnet market data is the default:

```bash
python cryptoquantbot.py fetch BTCUSDT --interval 60 --limit 500
```

That writes a local CSV under `data/`, which is intentionally ignored by Git.

Public mainnet candles can be requested for research without authentication:

```bash
python cryptoquantbot.py fetch BTCUSDT --interval 60 --limit 500 --mainnet
```

This command fetches market data only. It cannot access an account or place an order.

## CSV format

Close-only input remains valid:

```csv
date,close
2026-01-01,100.25
2026-01-02,101.10
```

OHLCV is also supported:

```csv
timestamp,open,high,low,close,volume
2026-01-01T00:00:00Z,100,105,98,103,42
```

## Project layout

```text
cryptoquantbot.py       CLI + backward-compatible facade
cqb/
  models.py             market/config/result models
  data.py               CSV ingestion and serialization
  indicators.py         dependency-free indicators
  strategies.py         strategy interfaces/reference models
  engine.py             deterministic execution simulator
  evaluation.py         benchmark, grid, walk-forward testing
  bybit.py              public market-data adapter only
  paper.py              local idempotent execution/risk contract
test_cryptoquantbot.py  unit tests
.github/workflows/       CI
SECURITY.md              credential/execution boundary
```

## Tests

```bash
python -m unittest -v test_cryptoquantbot.py
```

## Roadmap

The next engineering layer is **paper/testnet execution**, not immediate live trading. The intended progression is:

1. strengthen research metrics, multi-symbol evaluation, and regime testing;
2. integrate the earlier Bybit testnet work behind a clean exchange adapter;
3. add order-state reconciliation, risk ceilings, idempotency, and structured audit logs;
4. prove behavior under disconnects, retries, stale data, partial fills, and exchange errors;
5. only then consider a separately gated live-execution mode.

That separation is deliberate: strategy logic should be testable without exchange access, and exchange execution should not be trusted merely because a backtest runs.

## License

MIT. See [LICENSE](LICENSE).
