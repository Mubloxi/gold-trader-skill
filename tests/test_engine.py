import json
import os
from pathlib import Path
from datetime import timedelta
from tempfile import TemporaryDirectory
import unittest

from gold_desk.core import Bar, Feed, SPOT, ordered, ts, csv_feed, iso
from gold_desk.technical import atr, rsi, ema, scan, session_info, aligned_correlation, resample
from gold_desk.paper import Rules, Ledger, check_risk, new_state, size, step, make_plan
from gold_desk.replay import walk_forward, historical, monte_carlo

T=ts("2025-01-06T14:00:00Z")
FIX=Path(__file__).parent/"fixtures/synthetic-gold.csv"
def b(i=0,o=100,h=102,l=98,c=101):
    return Bar(T+timedelta(minutes=5*i),o,h,l,c)
def p(side=1):
    return {"instrument":SPOT,"at":iso(T),"side":side,"reference":100,
            "stop":95 if side==1 else 105,"target":112 if side==1 else 88}

class Technical(unittest.TestCase):
    def test_envelope_and_aware_alignment(self):
        with self.assertRaises(ValueError): b(h=99)
        with self.assertRaises(ValueError): b(c=float("nan"))
        with self.assertRaises(ValueError): ts("2025-01-06T10:00:00")
        with self.assertRaises(ValueError): ordered([b(),b()], "5m")
        with self.assertRaises(ValueError): ordered([b(1)], "15m")

    def test_wilder_rsi_edges(self):
        self.assertIsNone(rsi([1,2]))
        self.assertEqual(rsi([5]*15),50)
        self.assertEqual(rsi(list(range(15))),100)
        self.assertEqual(rsi(list(range(15,0,-1))),0)
        self.assertEqual(ema([10,11,12,13],3),[11,12])

    def test_atr_includes_gaps(self):
        self.assertAlmostEqual(atr([b(),b(1,120,124,119,123)],1),23)
        self.assertIsNone(atr([b()]))

    def test_resample_drops_partial_bucket(self):
        seven=[b(i,100,102+i,97-i,100+i) for i in range(1,8)]
        bars=resample(seven,"5m","15m")
        self.assertEqual([x.c for x in bars],[103,106])
        self.assertEqual(resample([b(1),b(3)],"5m","15m"),[])

    def test_gold_sessions_dst_and_holiday(self):
        # New York moved to DST, London has not yet.
        x=session_info(ts("2025-03-12T12:30:00Z"))
        self.assertTrue(x["overlap"])
        self.assertFalse(session_info(ts("2025-03-12T12:30:00Z"),{"2025-03-12":"closed"})["indicative_week_open"])
        self.assertFalse(session_info(ts("2025-03-15T12:30:00Z"))["indicative_week_open"])

    def test_correlation_on_changes_and_constants(self):
        x={i:i*i for i in range(20)}
        self.assertAlmostEqual(aligned_correlation(x,{k:-v for k,v in x.items()})["r"],-1)
        self.assertIsNone(aligned_correlation(x,{k:k for k in x})["r"])

    def test_closes_cutoff_and_feed_units(self):
        f=Feed([b(),b(1)],"5m","fixture",T+timedelta(minutes=5),synthetic=True)
        self.assertEqual(f.closed(T),[b()])
        self.assertEqual(f.provenance(T)["units"],"USD/troy oz")
        self.assertFalse(f.provenance(T+timedelta(hours=1))["fresh"])

class Paper(unittest.TestCase):
    def setUp(self):
        self.rules=Rules()
        self.s=new_state(self.rules)
    def test_costs_exposure_and_tamper_fingerprint(self):
        q=size(self.rules,self.s,p(),100)
        a=check_risk(self.rules,self.s,p(),100,q,b(1).close_time)
        bigger=check_risk(self.rules,self.s,p(),100,q*8,b(1).close_time)
        self.assertTrue(a["pass"])
        self.assertFalse(bigger["pass"])
        self.assertNotEqual(a["fingerprint"],bigger["fingerprint"])
        self.assertIn("virtual notional exceeds available collateral",bigger["reasons"])

    def test_daily_loss_drawdown_and_count_veto(self):
        self.s.update(day_loss=7.5,drawdown=.2,day_trades=6)
        q=size(self.rules,self.s,p(),100)
        r=check_risk(self.rules,self.s,p(),100,q,b(1).close_time)
        self.assertEqual(set(r["reasons"]),{"account drawdown limit","daily realized loss limit","daily trade count limit"})

    def test_ambiguous_stop_is_first(self):
        e=step(self.rules,self.s,b(1,100,115,90,100),"5m",p())
        self.assertEqual([y["type"] for y in e],["risk","open","close"])
        self.assertIn("ambiguous",e[-1]["reason"])
        self.assertLess(e[-1]["pnl"],0.)
        self.assertGreater(e[-1]["cost"],0.)
        self.assertIsNone(self.s["position"])

    def test_adverse_gap_and_missing_rows(self):
        step(self.rules,self.s,b(1),"5m",p())
        e=step(self.rules,self.s,b(4,88,96,84,90),"5m")
        self.assertEqual(e[0]["type"],"data_gap")
        self.assertEqual(e[-1]["reason"],"gap through stop")
        self.assertLess(e[-1]["exit"],88.)

    def test_next_bar_gap_voids_pending(self):
        self.assertEqual(step(self.rules,self.s,b(2),"5m",p())[0]["type"],"unfilled")

    def test_short_simulation_with_costs(self):
        e=step(self.rules,self.s,b(1,100,102,85,90),"5m",p(-1))
        self.assertGreater(e[-1]["pnl"],0.)
        self.assertEqual(e[-1]["position"]["side"],-1)

    def test_same_bar_forbidden_and_invalid_rules(self):
        self.assertFalse(check_risk(self.rules,self.s,p(),100,.1,T)["pass"])
        with self.assertRaises(ValueError): Rules(max_exposure=2)
        with self.assertRaises(ValueError): Rules(spread=0,slippage=0,commission_bps=0)

    def test_ledger_atomic_replay_duplicate_and_stale(self):
        with TemporaryDirectory() as tmp:
            l=Ledger(Path(tmp)/"test.sqlite")
            f=Feed([b(),b(1,100,120,97,115)],"5m","fixture",b(1).close_time,synthetic=True)
            l.apply(self.rules,f,T,p())
            applied=l.apply(self.rules,f,b(1).close_time)
            self.assertEqual(applied["events"][-1]["type"],"close")
            self.assertFalse(l.apply(self.rules,f,b(1).close_time)["events"])
            self.assertEqual(len(l.summary()["history"]),4)
            with self.assertRaises(ValueError): l.apply(self.rules,f,T+timedelta(hours=1))
            with self.assertRaises(ValueError): l.apply(Rules(initial=500),f,T)
            self.assertEqual(len(l.summary()["history"]),4)

class Replay(unittest.TestCase):
    def setUp(self):
        self.f=csv_feed(FIX,ts("2025-01-10T00:00:00Z"))
        self.r=Rules()
    def test_expanding_walk_forward_order_and_determinism(self):
        a=walk_forward(self.f.bars,"5m",self.r,samples=100)
        self.assertEqual(a,walk_forward(self.f.bars,"5m",self.r,samples=100))
        self.assertEqual(a["status"],"ok")
        self.assertEqual(len(a["test_folds"]),3)
        for x in a["test_folds"]:
            m=x["out_of_sample"]
            self.assertLess(x["training_end"],m["first_bar_closed_at"])
            self.assertEqual(m["trades"],m["wins"]+m["losses"]+m["flat"])
            self.assertIsInstance(m["buy_and_hold_pnl"],float)
        self.assertEqual(a["uncertainty"]["status"],"estimated")
    def test_future_bars_cannot_affect_prior_replay(self):
        bars=self.f.bars
        self.assertEqual(historical(bars,"5m",self.r,100,600),
                         historical(bars[:600],"5m",self.r,100,600))
    def test_sparse_bootstrap_is_not_invented(self):
        self.assertEqual(monte_carlo([1,2,3])["status"],"insufficient sample")
        values=[4,3,-4,1,2,3,-3,4,6]
        self.assertEqual(monte_carlo(values,seed=33,samples=100),
                         monte_carlo(values,seed=33,samples=100))
