import tempfile
import unittest
from pathlib import Path

from cryptoquantbot import PriceBar, backtest, generate_signals, load_prices
from cqb import (
    BacktestConfig,
    MovingAverageCrossStrategy,
    OrderRequest,
    OrderStatus,
    PaperBroker,
    RiskLimits,
    Side,
    backtest_strategy,
    buy_and_hold,
    ema,
    parameter_sensitivity,
    parse_kline_payload,
    rsi,
    sma,
    walk_forward,
)


def bars_from(closes):
    return [PriceBar(str(i), float(price)) for i, price in enumerate(closes)]


class SignalTests(unittest.TestCase):
    def test_rejects_invalid_windows(self):
        with self.assertRaises(ValueError):
            generate_signals([1, 2, 3], 5, 5)

    def test_no_lookahead(self):
        closes = [1, 1, 1, 1, 10]
        self.assertEqual(generate_signals(closes, 2, 4)[4], 0)

    def test_signal_is_deterministic(self):
        closes = [100 + i * 0.2 for i in range(50)]
        self.assertEqual(generate_signals(closes, 3, 10), generate_signals(closes, 3, 10))


class IndicatorTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 3), [None, None, 2.0, 3.0])

    def test_ema_shape(self):
        values = ema([1, 2, 3, 4, 5], 3)
        self.assertEqual(len(values), 5)
        self.assertIsNone(values[1])
        self.assertAlmostEqual(values[2], 2.0)

    def test_rsi_is_bounded(self):
        values = rsi([100, 101, 99, 102, 98, 103, 97, 104, 96, 105, 95, 106, 94, 107, 93, 108], 5)
        for value in values:
            if value is not None:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 100.0)


class BacktestTests(unittest.TestCase):
    def test_deterministic(self):
        closes = [100 + i for i in range(30)] + [130 - i * 1.5 for i in range(20)]
        bars = bars_from(closes)
        a = backtest(bars, fast_window=3, slow_window=8)
        b = backtest(bars, fast_window=3, slow_window=8)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a.trades, 2)
        self.assertGreater(a.ending_equity, 0)

    def test_fees_reduce_trending_strategy_result(self):
        bars = bars_from([100 + i for i in range(80)])
        free = backtest(bars, fast_window=3, slow_window=10, fee_bps=0)
        paid = backtest(bars, fast_window=3, slow_window=10, fee_bps=20)
        self.assertGreater(free.ending_equity, paid.ending_equity)

    def test_slippage_reduces_result(self):
        bars = bars_from([100 + i for i in range(80)])
        clean = backtest(bars, fast_window=3, slow_window=10, fee_bps=0, slippage_bps=0)
        slipped = backtest(bars, fast_window=3, slow_window=10, fee_bps=0, slippage_bps=25)
        self.assertGreater(clean.ending_equity, slipped.ending_equity)

    def test_csv_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("date,price\n2026-01-01,100\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_prices(path)

    def test_ohlcv_csv_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bars.csv"
            path.write_text(
                "timestamp,open,high,low,close,volume\n"
                "2026-01-01T00:00:00Z,100,110,90,105,42\n",
                encoding="utf-8",
            )
            loaded = load_prices(path)
            self.assertEqual(loaded[0].close, 105.0)
            self.assertEqual(loaded[0].volume, 42.0)

    def test_start_index_uses_warmup_only_for_signals(self):
        bars = bars_from([100 + i for i in range(40)])
        strategy = MovingAverageCrossStrategy(3, 10)
        cfg = BacktestConfig(fee_bps=0, stop_loss_pct=None)
        whole = backtest_strategy(bars, strategy, cfg)
        test_only = backtest_strategy(bars, strategy, cfg, start_index=20)
        self.assertNotEqual(whole.return_pct, test_only.return_pct)
        self.assertLess(test_only.exposure_pct, 100.01)

    def test_benchmark_uses_same_engine(self):
        bars = bars_from([100 + i for i in range(40)])
        result = buy_and_hold(bars, BacktestConfig(fee_bps=0, stop_loss_pct=None))
        self.assertGreater(result.return_pct, 0)
        self.assertEqual(result.round_trips, 1)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        trend1 = [100 + i * 0.5 for i in range(100)]
        pullback = [150 - i * 0.35 for i in range(50)]
        trend2 = [132.5 + i * 0.6 for i in range(120)]
        self.bars = bars_from(trend1 + pullback + trend2)

    def test_parameter_grid_is_ranked_and_valid(self):
        scores = parameter_sensitivity(self.bars[:150], (3, 5, 8), (15, 20, 30))
        self.assertTrue(scores)
        self.assertGreater(scores[0].return_pct, -100)
        self.assertLess(scores[0].fast_window, scores[0].slow_window)

    def test_walk_forward_is_deterministic(self):
        kwargs = dict(
            train_size=100,
            test_size=40,
            fast_windows=(3, 5, 8),
            slow_windows=(15, 20, 30),
        )
        first = walk_forward(self.bars, **kwargs)
        second = walk_forward(self.bars, **kwargs)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first.folds), 4)


class BybitParsingTests(unittest.TestCase):
    def test_parser_reorders_newest_first_payload(self):
        payload = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    ["2000", "11", "12", "10", "11.5", "9", "0"],
                    ["1000", "10", "11", "9", "10.5", "8", "0"],
                ]
            },
        }
        bars = parse_kline_payload(payload)
        self.assertEqual([bar.close for bar in bars], [10.5, 11.5])
        self.assertLess(bars[0].timestamp, bars[1].timestamp)

    def test_parser_rejects_exchange_error(self):
        with self.assertRaises(ValueError):
            parse_kline_payload({"retCode": 10001, "retMsg": "bad request"})


class PaperBrokerTests(unittest.TestCase):
    def test_retry_is_idempotent(self):
        broker = PaperBroker(starting_cash=10_000, limits=RiskLimits(2_000, 5_000))
        request = OrderRequest("order-1", "btcusdt", Side.BUY, 0.01)
        first = broker.submit(request, 50_000)
        after_first = broker.account
        second = broker.submit(request, 50_000)
        self.assertEqual(first, second)
        self.assertEqual(after_first, broker.account)
        self.assertEqual(first.status, OrderStatus.FILLED)

    def test_reused_id_with_different_effect_is_rejected(self):
        broker = PaperBroker()
        broker.submit(OrderRequest("same", "BTCUSDT", Side.BUY, 0.001), 50_000)
        with self.assertRaises(ValueError):
            broker.submit(OrderRequest("same", "ETHUSDT", Side.BUY, 0.001), 3_000)

    def test_risk_limit_rejects_without_mutation(self):
        broker = PaperBroker(starting_cash=10_000, limits=RiskLimits(500, 1_000))
        before = broker.account
        order = broker.submit(OrderRequest("risk", "BTCUSDT", Side.BUY, 0.02), 50_000)
        self.assertEqual(order.status, OrderStatus.REJECTED)
        self.assertEqual(before, broker.account)

    def test_cannot_sell_more_than_held(self):
        broker = PaperBroker(starting_cash=10_000, limits=RiskLimits(5_000, 8_000))
        order = broker.submit(OrderRequest("sell", "BTCUSDT", Side.SELL, 0.01), 50_000)
        self.assertEqual(order.status, OrderStatus.REJECTED)
        self.assertIn("insufficient position", order.reason)

    def test_buy_then_sell_updates_account(self):
        broker = PaperBroker(starting_cash=10_000, limits=RiskLimits(5_000, 8_000))
        broker.submit(OrderRequest("buy", "BTCUSDT", Side.BUY, 0.02), 50_000)
        self.assertAlmostEqual(broker.account.cash, 9_000)
        broker.submit(OrderRequest("sell", "BTCUSDT", Side.SELL, 0.02), 55_000)
        self.assertAlmostEqual(broker.account.cash, 10_100)
        self.assertNotIn("BTCUSDT", broker.account.positions)


if __name__ == "__main__":
    unittest.main()
