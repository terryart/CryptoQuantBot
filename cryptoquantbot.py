"""Deterministic crypto strategy backtester for educational research only."""
from __future__ import annotations
import argparse, csv, json
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Sequence

@dataclass(frozen=True)
class PriceBar:
    date: str
    close: float

@dataclass(frozen=True)
class BacktestResult:
    starting_cash: float
    ending_equity: float
    return_pct: float
    trades: int
    max_drawdown_pct: float
    def as_dict(self):
        return {
            "starting_cash": round(self.starting_cash, 2),
            "ending_equity": round(self.ending_equity, 2),
            "return_pct": round(self.return_pct, 2),
            "trades": self.trades,
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
        }

def load_prices(path: str | Path) -> list[PriceBar]:
    rows=[]
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if not {"date","close"}.issubset(reader.fieldnames or set()):
            raise ValueError("CSV must contain date and close columns")
        for raw in reader:
            close=float(raw["close"])
            if close <= 0: raise ValueError("close prices must be positive")
            rows.append(PriceBar(raw["date"], close))
    if not rows: raise ValueError("CSV contains no price rows")
    return rows

def generate_signals(closes: Sequence[float], fast_window=5, slow_window=20) -> list[int]:
    if fast_window <= 0 or slow_window <= 0: raise ValueError("windows must be positive")
    if fast_window >= slow_window: raise ValueError("fast_window must be smaller than slow_window")
    signals=[0]*len(closes)
    for i in range(slow_window, len(closes)):
        fast=fmean(closes[i-fast_window:i])
        slow=fmean(closes[i-slow_window:i])
        signals[i]=int(fast > slow)
    return signals

def _max_drawdown(curve: Sequence[float]) -> float:
    peak=curve[0]; worst=0.0
    for value in curve:
        peak=max(peak,value)
        worst=min(worst,(value-peak)/peak)
    return abs(worst)*100.0

def backtest(bars: Sequence[PriceBar], *, fast_window=5, slow_window=20,
             starting_cash=10000.0, fee_bps=10.0, position_fraction=0.95,
             stop_loss_pct=0.08) -> BacktestResult:
    if starting_cash <= 0: raise ValueError("starting_cash must be positive")
    if fee_bps < 0: raise ValueError("fee_bps cannot be negative")
    if not 0 < position_fraction <= 1: raise ValueError("position_fraction must be in (0, 1]")
    if stop_loss_pct is not None and not 0 < stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    closes=[b.close for b in bars]
    signals=generate_signals(closes, fast_window, slow_window)
    fee_rate=fee_bps/10000.0
    cash=starting_cash; units=0.0; entry=None; trades=0; curve=[]
    for bar, signal in zip(bars, signals):
        price=bar.close
        stopped=(units>0 and entry is not None and stop_loss_pct is not None
                 and price <= entry*(1-stop_loss_pct))
        if units>0 and (signal==0 or stopped):
            notional=units*price
            cash += notional-notional*fee_rate
            units=0.0; entry=None; trades += 1
        if units==0 and signal==1:
            spend=cash*position_fraction/(1+fee_rate)
            fee=spend*fee_rate
            units=spend/price
            cash -= spend+fee
            entry=price; trades += 1
        curve.append(cash+units*price)
    if units>0:
        notional=units*bars[-1].close
        cash += notional-notional*fee_rate
        trades += 1
        curve[-1]=cash
    ending=cash
    return BacktestResult(starting_cash, ending, (ending/starting_cash-1)*100,
                          trades, _max_drawdown(curve))

def main():
    p=argparse.ArgumentParser(description="Backtest a moving-average crossover on crypto CSV data.")
    p.add_argument("--csv", default="sample_prices.csv")
    p.add_argument("--fast", type=int, default=5)
    p.add_argument("--slow", type=int, default=20)
    p.add_argument("--cash", type=float, default=10000.0)
    p.add_argument("--fee-bps", type=float, default=10.0)
    p.add_argument("--position-fraction", type=float, default=0.95)
    p.add_argument("--stop-loss", type=float, default=0.08)
    a=p.parse_args()
    result=backtest(load_prices(a.csv), fast_window=a.fast, slow_window=a.slow,
                    starting_cash=a.cash, fee_bps=a.fee_bps,
                    position_fraction=a.position_fraction, stop_loss_pct=a.stop_loss)
    print(json.dumps(result.as_dict(), indent=2))

if __name__=="__main__":
    main()
