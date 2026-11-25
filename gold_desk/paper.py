"""Budget, independent veto and an exclusively local paper ledger."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
import json
import math
import sqlite3
from .core import FRAMES, SPOT, digest, iso, num, ts

@dataclass(frozen=True)
class Rules:
    initial: float = 250.
    risk_fraction: float = .01
    daily_loss_fraction: float = .03
    max_drawdown: float = .15
    max_exposure: float = 1.
    spread: float = .30            # full spread, USD / troy oz
    slippage: float = .05          # each side, USD / troy oz
    commission_bps: float = 1.     # each side, notional
    lot: float = .001              # virtual units only
    max_hold_bars: int = 12
    max_trades_day: int = 6

    def __post_init__(self):
        for x in asdict(self).values():
            num(x)
        if not (0<self.initial<=1e8 and 0<self.risk_fraction<=.05 and
                0<self.daily_loss_fraction<=.20 and 0<self.max_drawdown<=.70 and
                0<self.max_exposure<=1 and 0<=self.spread<=100 and 0<=self.slippage<=100 and
                0<=self.commission_bps<=500 and 0<self.lot<=100 and
                type(self.max_hold_bars) is int and 1<=self.max_hold_bars<=10000 and
                type(self.max_trades_day) is int and 1<=self.max_trades_day<=100):
            raise ValueError("invalid simulated account rules")
        if self.spread+self.slippage+self.commission_bps<=0:
            raise ValueError("zero-cost paper mode not supported")

    @property
    def impact(self):
        return self.spread/2+self.slippage

    def fill(self,reference,side,entry):
        v=reference+(side if entry else -side)*self.impact
        if v<=0:
            raise ValueError("simulated execution price not positive")
        return v

    def fee(self,price,qty):
        return price*qty*self.commission_bps/10000

def make_plan(bars,lookback=20,reward=2.0):
    from .technical import atr
    if len(bars)<max(lookback+1,22):
        return None
    prev=bars[-lookback-1:-1]
    b=bars[-1]
    vol=atr(bars)
    side=1 if b.c>max(p.h for p in prev) else -1 if b.c<min(p.l for p in prev) else 0
    if not side or not vol:
        return None
    dist=max(.1,vol*1.5)
    if min(b.c-dist,b.c-dist*reward)<=0:
        return None
    return {"instrument":SPOT,"at":iso(b.close_time),"side":side,"reference":b.c,
            "stop":b.c-side*dist,"target":b.c+side*dist*reward,"lookback":lookback,
            "purpose":"hypothetical breakout research"}

def new_state(r):
    return {"initial":r.initial,"balance":r.initial,"equity":r.initial,"peak":r.initial,
            "drawdown":0.,"max_drawdown":0.,"total_cost":0.,"position":None,"cursor":None,
            "day":None,"day_loss":0.,"day_start":r.initial,"day_trades":0}

def day_sync(state,b):
    day=b.close_time.date().isoformat()
    if day!=state["day"]:
        state.update(day=day,day_loss=0.,day_start=state["equity"],day_trades=0)

def per_unit_loss(r,opening,stop,side):
    ent,ext=r.fill(opening,side,True),r.fill(stop,side,False)
    return side*(ent-ext)+r.fee(ent,1)+r.fee(ext,1)

def size(r,state,plan,opening):
    """Sizing proposes; check_risk independently recomputes the result."""
    ent=r.fill(opening,plan["side"],True)
    unit=per_unit_loss(r,opening,plan["stop"],plan["side"])
    if unit<=0:
        return 0.
    exposure=min(state["equity"],state["balance"])*r.max_exposure
    raw=min(state["equity"]*r.risk_fraction/unit,exposure/(ent+r.fee(ent,1)))
    return max(0.,round(math.floor(raw/r.lot)*r.lot,12))

def check_risk(r,state,plan,opening,qty,closed_at):
    reasons=[]
    try:
        side=plan["side"]
        if type(side) is not int or side not in (-1,1) or plan["instrument"]!=SPOT:
            raise ValueError("invalid plan identity")
        opening,stop,target,qty=map(num,(opening,plan["stop"],plan["target"],qty))
        if ts(plan["at"])>=closed_at:
            reasons.append("fill bar must close after the signal")
        if min(opening,stop,target)<=0 or side*(opening-stop)<=0 or side*(target-opening)<=0:
            reasons.append("opening price breached the hypothetical bracket")
        if state["position"] is not None:
            reasons.append("one position cap")
        if state["equity"]<=0 or state["drawdown"]>=r.max_drawdown:
            reasons.append("account drawdown limit")
        if state["day_loss"]>=r.daily_loss_fraction*max(0.,state["day_start"]):
            reasons.append("daily realized loss limit")
        if state["day_trades"]>=r.max_trades_day:
            reasons.append("daily trade count limit")
        unit=per_unit_loss(r,opening,stop,side)
        entry,exit=r.fill(opening,side,True),r.fill(target,side,False)
        reward=side*(exit-entry)-r.fee(entry,1)-r.fee(exit,1)
        if unit<=0 or reward<unit:
            reasons.append("net reward/risk below one")
        if qty<=0 or abs(qty/r.lot-round(qty/r.lot))>1e-7:
            reasons.append("invalid virtual quantity")
        if qty*unit>state["equity"]*r.risk_fraction+1e-8:
            reasons.append("planned loss exceeds budget after costs")
        if qty*(entry+r.fee(entry,1))>min(state["equity"],state["balance"])*r.max_exposure+1e-8:
            reasons.append("virtual notional exceeds available collateral")
    except (ValueError,KeyError,TypeError,OverflowError):
        reasons.append("invalid risk inputs")
    return {"pass":not reasons,"reasons":reasons,
            "at":iso(closed_at),"fingerprint":digest([plan,opening,qty,iso(closed_at),asdict(r),state])}

def close_position(r,state,reference,reason,b):
    p=state["position"]
    exit=r.fill(reference,p["side"],False)
    fee=r.fee(exit,p["qty"])
    pnl=p["side"]*(exit-p["entry"])*p["qty"]-p["fee"]-fee
    costs=p["fee"]+fee+((p["entry"]-p["entry_reference"])*p["side"]+
                       (reference-exit)*p["side"])*p["qty"]
    state["balance"]+=pnl
    state["total_cost"]+=costs
    state["day_loss"]+=max(0.,-pnl)
    state["position"]=None
    return {"type":"close","at":iso(b.close_time),"exit":exit,"exit_reference":reference,
            "pnl":pnl,"cost":costs,"reason":reason,"position":p}

def step(r,state,b,frame,plan=None):
    """Consume one completed bar; risk cannot be supplied by callers."""
    if state["cursor"] and ts(state["cursor"])>=b.close_time:
        raise ValueError("cannot replay or reorder a consumed bar")
    day_sync(state,b)
    events=[]
    p=state["position"]
    if p and state["cursor"] and b.close_time-ts(state["cursor"])!=timedelta(minutes=FRAMES[frame]):
        events.append({"type":"data_gap","at":iso(b.close_time),
                       "reason":"holding period has missing bars; only observed prices can be modeled"})
    if plan and p is None:
        if b.close_time-ts(plan["at"])!=timedelta(minutes=FRAMES[frame]):
            events.append({"type":"unfilled","at":iso(b.close_time),"reason":"first contiguous bar unavailable"})
        else:
            try:
                qty=size(r,state,plan,b.o)
            except (ValueError,KeyError,TypeError,OverflowError):
                qty=0.
            verdict=check_risk(r,state,plan,b.o,qty,b.close_time)
            events.append({"type":"risk","at":iso(b.close_time),"verdict":verdict})
            if verdict["pass"]:
                entry=r.fill(b.o,plan["side"],True)
                p={"at":iso(b.close_time),"signal_at":plan["at"],"side":plan["side"],"qty":qty,
                   "entry":entry,"entry_reference":b.o,"fee":r.fee(entry,qty),
                   "stop":plan["stop"],"target":plan["target"],"bars":0,
                   "risk_fingerprint":verdict["fingerprint"],"regime":plan.get("regime","unknown")}
                state["position"]=p
                state["day_trades"]+=1
                events.append({"type":"open","at":iso(b.close_time),"position":dict(p)})
    if p:
        p["bars"]+=1
        if p["side"]==1:
            adverse=b.l<=p["stop"]
            favorable=b.h>=p["target"]
            gap=b.o<=p["stop"]
        else:
            adverse=b.h>=p["stop"]
            favorable=b.l<=p["target"]
            gap=b.o>=p["stop"]
        if adverse:
            events.append(close_position(r,state,b.o if gap else p["stop"],
                              "gap through stop" if gap else "stop before ambiguous target" if favorable else "stop",b))
        elif favorable:
            events.append(close_position(r,state,p["target"],"target (no gap improvement)",b))
        elif p["bars"]>=r.max_hold_bars:
            events.append(close_position(r,state,b.c,"observed bar time limit",b))
    p=state["position"]
    state["equity"]=state["balance"]
    if p:
        px=r.fill(b.c,p["side"],False)
        state["equity"]+=p["side"]*(px-p["entry"])*p["qty"]-p["fee"]-r.fee(px,p["qty"])
    state["peak"]=max(state["peak"],state["equity"])
    state["drawdown"]=(state["peak"]-state["equity"])/state["peak"]
    state["max_drawdown"]=max(state["max_drawdown"],state["drawdown"])
    state["cursor"]=iso(b.close_time)
    return events

class Ledger:
    def __init__(self,path):
        path=Path(path)
        path.parent.mkdir(parents=True,exist_ok=True)
        self.path=path

    @contextmanager
    def txn(self):
        c=sqlite3.connect(self.path,timeout=10)
        try:
            c.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT NOT NULL, body TEXT NOT NULL)")
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def apply(self,r,feed,as_of,plan=None,max_age=10):
        bars=feed.closed(as_of)
        p=feed.provenance(as_of,max_age)
        if not p["fresh"] or feed.quote_kind not in {"mid","indicative"}:
            raise ValueError("paper execution needs fresh mid/indicative spot bars")
        signature=[SPOT,feed.source,feed.frame,feed.quote_kind,feed.synthetic]
        with self.txn() as c:
            old=c.execute("SELECT body FROM account WHERE id=1").fetchone()
            data=json.loads(old[0]) if old else dict(rules=asdict(r),signature=signature,
                                                    state=new_state(r),pending=None)
            if data["signature"]!=signature or data["rules"]!=asdict(r):
                raise ValueError("ledger is pinned to its feed and rules")
            s=data["state"]
            behind=s["cursor"]
            if not old:
                s["cursor"]=iso(bars[-1].close_time)
            elif s["position"] and not any(iso(b.close_time)==behind for b in bars):
                raise ValueError("position history missing the ledger cursor; import overlapping candles")
            events=[]
            for b in bars:
                if s["cursor"] is None or b.close_time>ts(s["cursor"]):
                    events+=step(r,s,b,feed.frame,data["pending"])
                    data["pending"]=None
            if plan:
                if plan["at"]!=s["cursor"] or s["position"] or data["pending"]:
                    raise ValueError("paper plan needs the latest completed bar and a flat idle account")
                data["pending"]=plan
                events.append({"type":"hypothesis","at":s["cursor"],"plan":plan})
            for e in events:
                c.execute("INSERT INTO events(at, body) VALUES(?,?)",(e["at"],json.dumps(e,allow_nan=False)))
            c.execute("INSERT OR REPLACE INTO account(id,body) VALUES(1,?)",(json.dumps(data,allow_nan=False),))
            return {"state":s,"events":events,"pending":data["pending"],"mode":"simulation","feed":p}

    def summary(self):
        with self.txn() as c:
            row=c.execute("SELECT body FROM account WHERE id=1").fetchone()
            if not row:
                return {"mode":"simulation","account":None}
            d=json.loads(row[0])
            history=[json.loads(v[0]) for v in c.execute("SELECT body FROM events ORDER BY id")]
            days={}
            for e in history:
                s=days.setdefault(e["at"][:10],{"closed":0,"pnl":0.,"cost":0.,"vetoes":0})
                if e["type"]=="close":
                    s["closed"]+=1
                    s["pnl"]+=e["pnl"]
                    s["cost"]+=e["cost"]
                if e["type"]=="risk" and not e["verdict"]["pass"]:
                    s["vetoes"]+=1
            return {"mode":"simulation","account":d,"history":history,"sessions_utc":days,
                    "realized_pnl":d["state"]["balance"]-d["state"]["initial"],
                    "unrealized_pnl_net_of_modeled_exit":d["state"]["equity"]-d["state"]["balance"]}
