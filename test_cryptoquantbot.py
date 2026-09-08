import tempfile, unittest
from pathlib import Path
from cryptoquantbot import PriceBar, backtest, generate_signals, load_prices

class SignalTests(unittest.TestCase):
    def test_rejects_invalid_windows(self):
        with self.assertRaises(ValueError):
            generate_signals([1,2,3],5,5)
    def test_no_lookahead(self):
        closes=[1,1,1,1,10]
        self.assertEqual(generate_signals(closes,2,4)[4],0)

class BacktestTests(unittest.TestCase):
    def test_deterministic(self):
        closes=[100+i for i in range(30)] + [130-i*1.5 for i in range(20)]
        bars=[PriceBar(str(i),p) for i,p in enumerate(closes)]
        a=backtest(bars,fast_window=3,slow_window=8)
        b=backtest(bars,fast_window=3,slow_window=8)
        self.assertEqual(a,b)
        self.assertGreaterEqual(a.trades,2)
        self.assertGreater(a.ending_equity,0)
    def test_csv_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.csv"; p.write_text("date,price\\n2026-01-01,100\\n")
            with self.assertRaises(ValueError): load_prices(p)

if __name__=="__main__": unittest.main()
