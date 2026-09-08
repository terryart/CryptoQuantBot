# Security

CryptoQuantBot's public repository is a **research/backtesting project**. The current public code can fetch unauthenticated market candles, but it does not contain an authenticated exchange client or an order-placement path.

## Credentials

Do not commit API keys, API secrets, private keys, session cookies, `.env` files, or exchange account exports. Local secret/config files are ignored by `.gitignore`.

If authenticated exchange support is added in the future, credentials should be loaded from environment variables or a dedicated secret store and should never appear in logs, fixtures, screenshots, notebooks, or example commands.

## Reporting a problem

If you find a credential leak, unsafe execution path, or security-sensitive defect, avoid opening an issue that exposes the sensitive material. Contact the repository owner privately first.

## Trading safety boundary

A backtest result is not evidence of live profitability. Fees, slippage, liquidity, latency, funding, liquidation behavior, exchange outages, and regime change can materially alter real execution. The public project should preserve a clear separation between research, paper/testnet execution, and any future live execution path.
