"""CryptoQuantBot research engine."""

from .bybit import fetch_bybit_klines, parse_kline_payload
from .data import load_prices, write_prices
from .engine import backtest_strategy, max_drawdown
from .evaluation import buy_and_hold, parameter_sensitivity, walk_forward
from .indicators import bollinger_bands, ema, rsi, sma
from .paper import OrderRequest, OrderStatus, PaperAccount, PaperBroker, PaperOrder, RiskLimits, Side
from .models import (
    BacktestConfig,
    BacktestResult,
    ParameterScore,
    PriceBar,
    WalkForwardFold,
    WalkForwardResult,
)
from .strategies import (
    EMATrendStrategy,
    MovingAverageCrossStrategy,
    RSIMeanReversionStrategy,
    generate_ma_signals,
)

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "EMATrendStrategy",
    "MovingAverageCrossStrategy",
    "ParameterScore",
    "OrderRequest",
    "OrderStatus",
    "PaperAccount",
    "PaperBroker",
    "PaperOrder",
    "RiskLimits",
    "Side",
    "PriceBar",
    "RSIMeanReversionStrategy",
    "WalkForwardFold",
    "WalkForwardResult",
    "backtest_strategy",
    "bollinger_bands",
    "buy_and_hold",
    "ema",
    "fetch_bybit_klines",
    "generate_ma_signals",
    "load_prices",
    "max_drawdown",
    "parameter_sensitivity",
    "parse_kline_payload",
    "rsi",
    "sma",
    "walk_forward",
    "write_prices",
]
