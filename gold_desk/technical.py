"""Deterministic statistics. RSI recurrence adapted from upstream scan.py."""
from collections import defaultdict
from datetime import datetime, timedelta
from math import log
from statistics import fmean, pstdev, correlation
from zoneinfo import ZoneInfo
from .core import Bar, FRAMES, UTC, iso

def ema(xs,n):
    if len(xs)<n:
        return []
    out=[fmean(xs[:n])]
    for x in xs[n:]:
        out.append(out[-1]+(x-out[-1])*2/(n+1))
    return out

def rma(xs,n):
    """Wilder smoothing, seeded with the first n values’ simple mean."""
    if n <= 0 or len(xs) < n:
        return []
    out=[fmean(xs[:n])]
    for x in xs[n:]:
        out.append((out[-1]*(n-1)+x)/n)
    return out

def candle_values(b):
    return {"close_time":iso(b.close_time),"open":b.o,"high":b.h,"low":b.l,"close":b.c,
            "body":abs(b.c-b.o),"range":b.h-b.l,"upper_wick":b.h-max(b.o,b.c),
            "lower_wick":min(b.o,b.c)-b.l,"direction":"up" if b.c>b.o else "down" if b.c<b.o else "flat"}

def rsi(xs,n=14):
    if len(xs)<n+1:
        return None
    d=[b-a for a,b in zip(xs,xs[1:])]
    g=[max(x,0.) for x in d]
    l=[max(-x,0.) for x in d]
    a,b=fmean(g[:n]),fmean(l[:n])
    for i in range(n,len(d)):
        a,b=((n-1)*a+g[i])/n,((n-1)*b+l[i])/n
    return 100-100/(1+a/b) if b else (100. if a else 50.)

def atr(bars,n=14):
    if len(bars)<n+1:
        return None
    tr=[max(b.h-b.l,abs(b.h-a.c),abs(b.l-a.c)) for a,b in zip(bars,bars[1:])]
    v=fmean(tr[:n])
    for x in tr[n:]:
        v=((n-1)*v+x)/n
    return v

def resample(bars,source,target):
    s,t=FRAMES[source],FRAMES[target]
    if t<s or t%s:
        raise ValueError("target must be a multiple of source frame")
    groups=defaultdict(list)
    for b in bars:
        epoch=int(b.close_time.timestamp())
        groups[((epoch-1)//(t*60)+1)*t*60].append(b)
    return [Bar(datetime.fromtimestamp(k,UTC),v[0].o,max(b.h for b in v),
                min(b.l for b in v),v[-1].c) for k,v in sorted(groups.items()) if len(v)==t//s]

def scan(bars):
    if not bars:
        return {"bars":0,"status":"insufficient"}
    xs=[b.c for b in bars]
    avg={str(n):fmean(xs[-n:]) if len(xs)>=n else None for n in (10,20,50)}
    fast,slow=ema(xs,12),ema(xs,26)
    line=[a-b for a,b in zip(fast[-len(slow):],slow)] if slow else []
    sig=ema(line,9)
    look=bars[-21:-1]
    ceiling=max(b.h for b in look) if len(look)==20 else None
    floor=min(b.l for b in look) if ceiling is not None else None
    swing10=bars[-10:]
    previous=bars[-20:-10]
    structure=None
    if len(previous)==10:
        hi=max(x.h for x in swing10)-max(x.h for x in previous)
        lo=min(x.l for x in swing10)-min(x.l for x in previous)
        structure="higher highs and lows" if hi>0 and lo>0 else "lower highs and lows" if hi<0 and lo<0 else "mixed"
    trend="insufficient"
    if avg["50"] is not None:
        trend="up" if xs[-1]>avg["20"]>avg["50"] else "down" if xs[-1]<avg["20"]<avg["50"] else "range/mixed"
    returns=[log(b/a) for a,b in zip(xs[-21:-1],xs[-20:])] if len(xs)>=21 else []
    exp={str(n): series[-1] if (series:=ema(xs,n)) else None for n in (9,20,50,200)}
    smooth=rma(xs,14)
    return {"bars":len(bars),"last":xs[-1],"at":iso(bars[-1].close_time),
            "ema":exp,"rma14":smooth[-1] if smooth else None,"latest_candle":candle_values(bars[-1]),
            "sma":avg,"rsi14":rsi(xs),"atr14":atr(bars),
            "macd":{"line":line[-1] if line else None,"signal":sig[-1] if sig else None,
                    "histogram":line[-1]-sig[-1] if sig else None},
            "volatility_log_per_bar":pstdev(returns) if returns else None,
            "support":floor,"resistance":ceiling,"structure":structure,"regime":trend,
            "breakout":"above" if ceiling is not None and xs[-1]>ceiling else
                       "below" if floor is not None and xs[-1]<floor else "none"}

SESSIONS={"Asia (Tokyo)":("Asia/Tokyo",9,17),"London":("Europe/London",8,17),
          "New York":("America/New_York",8,17)}

def session_info(d,exceptions=None):
    """Indicative desk windows, not an executable market-hours promise."""
    exceptions=exceptions or {}
    ny=d.astimezone(ZoneInfo("America/New_York"))
    gold_week=(ny.weekday()<4 and ny.hour!=17) or (ny.weekday()==4 and ny.hour<17) or (ny.weekday()==6 and ny.hour>=18)
    override=exceptions.get(ny.date().isoformat())
    if override=="closed":
        gold_week=False
    elif isinstance(override,int):
        gold_week=gold_week and ny.hour<override
    active=[]
    for name,(zone,start,end) in SESSIONS.items():
        local=d.astimezone(ZoneInfo(zone))
        if gold_week and local.weekday()<5 and start<=local.hour<end:
            active.append(name)
    return {"active":active,"overlap":len(active)>1,"indicative_week_open":gold_week,"holiday_override":override}

def session_levels(bars,exceptions=None,frame="5m"):
    groups={}
    for b in bars:
        t=b.close_time-timedelta(microseconds=1)
        for name in session_info(t,exceptions)["active"]:
            zone,start,_=SESSIONS[name]
            if (b.close_time-timedelta(minutes=FRAMES[frame])).astimezone(ZoneInfo(zone)).hour < start:
                continue
            day=t.astimezone(ZoneInfo(zone)).date().isoformat()
            key=f"{day} {name}"
            cur=groups.setdefault(key,{"high":b.h,"low":b.l,"bars":0})
            cur.update(high=max(cur["high"],b.h),low=min(cur["low"],b.l),bars=cur["bars"]+1)
    return dict(sorted(groups.items())[-12:])

def aligned_correlation(x,y,limit=60):
    """Pearson on synchronous one-period changes, never level correlations."""
    keys=sorted(set(x)&set(y))[-(limit+1):]
    pairs=[(x[b]-x[a],y[b]-y[a]) for a,b in zip(keys,keys[1:])]
    if len(pairs)<10:
        return {"n":len(pairs),"r":None}
    try:
        return {"n":len(pairs),"r":correlation(*zip(*pairs))}
    except (ValueError, ArithmeticError):
        return {"n":len(pairs),"r":None}
