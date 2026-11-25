"""Chronological tests, simple benchmarks and seeded contiguous trade bootstrap."""
from collections import defaultdict
from random import Random
from statistics import fmean, median, stdev
from .core import iso
from .paper import make_plan, new_state, step

def metric(closed,state):
    pnl=[x["pnl"] for x in closed]
    w=[x for x in pnl if x>0]
    l=[x for x in pnl if x<0]
    return {"trades":len(pnl),"pnl":sum(pnl),"expectancy":fmean(pnl) if pnl else None,
            "profit_factor":sum(w)/-sum(l) if l else None,"wins":len(w),"losses":len(l),
            "flat":len(pnl)-len(w)-len(l),"median_win":median(w) if w else None,
            "median_loss":median(l) if l else None,"win_distribution":w,"loss_distribution":l,
            "equity":state["equity"],"max_drawdown":state["max_drawdown"],
            "costs":state["total_cost"],"open_at_end":bool(state["position"])}

def historical(bars,frame,r,start,end,lookback=20):
    s=new_state(r)
    closed=[]
    grouped=defaultdict(list)
    vetoes=0
    plan=None
    for i in range(start,end):
        b=bars[i]
        ev=step(r,s,b,frame,plan)
        for x in ev:
            if x["type"]=="close":
                closed.append(x)
                grouped[x["position"]["regime"]].append(x["pnl"])
            if x["type"]=="risk" and not x["verdict"]["pass"]:
                vetoes+=1
        history=bars[max(0,i-60):i+1]
        plan=make_plan(history,lookback) if not s["position"] else None
        if plan and len(history)>=50:
            c=[bar.c for bar in history[-50:]]
            z=fmean(c[:25])
            m=fmean(c[25:])
            plan["regime"]="rising" if m>z*1.001 else "falling" if m<z*.999 else "flat"
    ent=r.fill(bars[start].o,1,True)
    ext=r.fill(bars[end-1].c,1,False)
    qty=r.initial/(ent+r.fee(ent,1))
    hold=(ext-ent)*qty-r.fee(ent,qty)-r.fee(ext,qty)
    return metric(closed,s)|{"first_bar_closed_at":iso(bars[start].close_time),"last_bar_closed_at":iso(bars[end-1].close_time),
                "vetoes":vetoes,"cash_benchmark_pnl":0.,"buy_and_hold_pnl":hold,
                "by_regime":{k:{"trades":len(v),"pnl":sum(v),"expectancy":fmean(v)} for k,v in grouped.items()},"trade_pnl":[x["pnl"] for x in closed]}

def monte_carlo(values,seed=19,samples=1000,block=4):
    if type(seed) is not int or not 100<=samples<=20000 or block<1:
        raise ValueError("invalid bootstrap settings")
    if len(values)<8:
        return {"status":"insufficient sample","trades":len(values),"seed":seed,"samples":0}
    rng=Random(seed)
    block=min(block,len(values))
    out=[]
    for _ in range(samples):
        draw=[]
        while len(draw)<len(values):
            i=rng.randrange(len(values)-block+1)
            draw.extend(values[i:i+block])
        out.append(fmean(draw[:len(values)]))
    out.sort()
    return {"status":"estimated","trades":len(values),"seed":seed,"samples":samples,"block":block,
            "bootstrap_expectancy_ci95":[out[int((samples-1)*.025)],out[int((samples-1)*.975)]],
            "bootstrap_fraction_negative":sum(x<0 for x in out)/len(out),
            "note":"Resamples modeled out-of-sample trade P&L. Conditional on this sample, not a forecast."}

def walk_forward(bars,frame,r,seed=19,folds=3,samples=1000):
    if folds not in range(1,9) or len(bars)<max(180,60+30*folds):
        return {"status":"insufficient bars","bars":len(bars),"folds":folds}
    first=len(bars)//2
    width=(len(bars)-first)//folds
    results=[]
    pnl=[]
    for j in range(folds):
        start=first+j*width
        end=len(bars) if j==folds-1 else start+width
        scores={}
        for n in (15,20,30):
            m=historical(bars,frame,r,40,start,n)
            x=m["trade_pnl"]
            # Penalize drawdown and sampling uncertainty instead of maximizing gross return.
            scores[n]=(fmean(x)-stdev(x)/(len(x)**.5)-r.initial*m["max_drawdown"]/len(x)) if len(x)>=8 else None
        usable=[k for k,v in scores.items() if v is not None]
        selected=max(usable,key=lambda n:(scores[n],-abs(n-20))) if usable else 20
        forward=historical(bars,frame,r,start,end,selected)
        pnl+=forward["trade_pnl"]
        results.append({"training_end":iso(bars[start-1].close_time),"training_scores":scores,
                        "selected_lookback":selected,"default_without_training_evidence":not usable,
                        "out_of_sample":forward})
    return {"status":"ok","method":"expanding training window; disjoint forward folds; flat/reset at fold starts",
            "test_folds":results,"out_of_sample_trade_pnl":sum(pnl),
            "uncertainty":monte_carlo(pnl,seed,samples),
            "limitations":"Independent fold balances are not compounded. Open positions are marked, not treated as realized."}
