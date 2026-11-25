from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase

from gold_desk.core import MT5_GOLD
from gold_desk.mt5_feed import read_mt5, ProviderError
from gold_desk.paper import Rules
from gold_desk.technical import candle_values, rma, scan
from gold_desk.workflow import snapshot

NOW = datetime(2025,1,9,19,40,tzinfo=timezone.utc)

class Stub:
    TIMEFRAME_M5 = 5

    def __init__(self):
        self.closed = False
        self.connected = True
        self.spec = SimpleNamespace(currency_base="XAU",currency_profit="USD",
                                    chart_mode=0,expiration_time=0)
        self.t = NOW

    def initialize(self, *args, **kwargs):
        assert not args and kwargs == {"timeout":10000}
        return True

    def terminal_info(self):
        return SimpleNamespace(connected=self.connected)

    def account_info(self):
        return SimpleNamespace(trade_mode=0)

    def symbol_info(self, symbol):
        return self.spec if symbol == "XAUUSD.a" else None

    def copy_rates_from_pos(self, symbol, timeframe, position, count):
        assert (symbol,timeframe,position,count) == ("XAUUSD.a",5,1,40)
        return [{"time":int((self.t-timedelta(minutes=5*(40-i))).timestamp()),
                 "open":2600+i,"high":2604+i,"low":2597+i,"close":2602+i}
                for i in range(40)]

    def symbol_info_tick(self,symbol):
        return SimpleNamespace(time_msc=int((NOW-timedelta(seconds=1)).timestamp()*1000),
                               bid=2641.1,ask=2641.3)

    def shutdown(self):
        self.closed = True

class TestMT5(TestCase):
    def read(self, stub):
        return read_mt5("XAUUSD.a","5m",40,api=stub,clock=lambda: NOW)

    def test_closed_bars_quotes_and_indicators(self):
        stub=Stub()
        f=self.read(stub)
        self.assertTrue(stub.closed)
        self.assertEqual(f.instrument,MT5_GOLD)
        self.assertEqual(f.bars[-1].close_time,NOW)
        p=f.provenance(NOW)
        self.assertTrue(p["last_quote"]["fresh"])
        self.assertAlmostEqual(p["last_quote"]["spread_usd_per_oz"],0.2)
        self.assertTrue(candle_values(f.bars[-1])["upper_wick"]==2)
        self.assertEqual(scan(f.bars)["latest_candle"]["lower_wick"],3)
        self.assertIsNotNone(scan(f.bars)["macd"]["signal"])
        self.assertIsNone(scan(f.bars)["ema"]["200"])
        self.assertEqual(rma([2,4,6],2),[3.0,4.5])
        self.assertFalse(f.provenance(NOW+timedelta(hours=1))["fresh"])

    def test_broker_research_not_paper_execution(self):
        data=snapshot(self.read(Stub()),NOW,"quick",Rules(),[],[],10,{})
        self.assertIsNone(data["paper_hypothesis"])
        self.assertEqual(data["evidence"][0]["series"],"BROKER_OHLC")
        self.assertEqual(len(data["technical"]["5m"]["recent_candles"]),8)

    def test_wrong_instrument_disconnect_and_future_candle(self):
        for edit,msg in [
            (lambda x:setattr(x.spec,"currency_base","BTC"),"non-expiring XAU/USD"),
            (lambda x:setattr(x,"connected",False),"disconnected"),
            (lambda x:setattr(x,"t",NOW+timedelta(minutes=5)),"future time"),
        ]:
            stub=Stub()
            edit(stub)
            with self.assertRaisesRegex(ProviderError,msg):
                self.read(stub)
            self.assertTrue(stub.closed)
