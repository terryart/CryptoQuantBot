"""Local paper-execution state machine.

This module deliberately does not talk to an exchange. It gives the research project an
execution contract with idempotency and risk rejection before a real testnet adapter is
allowed to implement the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    FILLED = "filled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: float = 1_000.0
    max_open_notional: float = 2_500.0

    def __post_init__(self) -> None:
        if self.max_order_notional <= 0 or self.max_open_notional <= 0:
            raise ValueError("risk limits must be positive")
        if self.max_order_notional > self.max_open_notional:
            raise ValueError("max_order_notional cannot exceed max_open_notional")


@dataclass(frozen=True)
class OrderRequest:
    client_order_id: str
    symbol: str
    side: Side
    quantity: float

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True)
class PaperOrder:
    client_order_id: str
    symbol: str
    side: Side
    quantity: float
    fill_price: float | None
    status: OrderStatus
    reason: str | None = None


@dataclass(frozen=True)
class PaperAccount:
    cash: float
    positions: dict[str, float]


class PaperBroker:
    """Immediate-fill local broker used to prove execution invariants."""

    def __init__(self, starting_cash: float = 10_000.0, limits: RiskLimits | None = None):
        if starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        self._cash = float(starting_cash)
        self._positions: dict[str, float] = {}
        self._orders: dict[str, PaperOrder] = {}
        self._limits = limits or RiskLimits()

    @property
    def account(self) -> PaperAccount:
        return PaperAccount(self._cash, dict(self._positions))

    def submit(self, request: OrderRequest, market_price: float) -> PaperOrder:
        if market_price <= 0:
            raise ValueError("market_price must be positive")

        # Idempotency is non-negotiable: retrying a client order ID returns the original
        # outcome and never applies its effects twice.
        existing = self._orders.get(request.client_order_id)
        if existing is not None:
            if (
                existing.symbol != request.symbol.upper()
                or existing.side != request.side
                or existing.quantity != request.quantity
            ):
                raise ValueError("client_order_id was already used for a different order")
            return existing

        symbol = request.symbol.upper()
        notional = request.quantity * market_price
        if notional > self._limits.max_order_notional:
            return self._record_rejection(request, symbol, "max_order_notional exceeded")

        held = self._positions.get(symbol, 0.0)
        if request.side is Side.BUY:
            open_notional = held * market_price
            if open_notional + notional > self._limits.max_open_notional:
                return self._record_rejection(request, symbol, "max_open_notional exceeded")
            if notional > self._cash:
                return self._record_rejection(request, symbol, "insufficient cash")
            self._cash -= notional
            self._positions[symbol] = held + request.quantity
        else:
            if request.quantity > held:
                return self._record_rejection(request, symbol, "insufficient position")
            self._cash += notional
            remaining = held - request.quantity
            if remaining == 0:
                self._positions.pop(symbol, None)
            else:
                self._positions[symbol] = remaining

        order = PaperOrder(
            client_order_id=request.client_order_id,
            symbol=symbol,
            side=request.side,
            quantity=request.quantity,
            fill_price=market_price,
            status=OrderStatus.FILLED,
        )
        self._orders[request.client_order_id] = order
        return order

    def _record_rejection(self, request: OrderRequest, symbol: str, reason: str) -> PaperOrder:
        order = PaperOrder(
            client_order_id=request.client_order_id,
            symbol=symbol,
            side=request.side,
            quantity=request.quantity,
            fill_price=None,
            status=OrderStatus.REJECTED,
            reason=reason,
        )
        self._orders[request.client_order_id] = order
        return order
