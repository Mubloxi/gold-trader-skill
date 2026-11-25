"""Command-line entry point. No brokerage or model API clients."""
import argparse
from datetime import timedelta
from pathlib import Path
import sys
from .core import MT5_GOLD, csv_feed, json_text, read_json, now, ts, digest, write_json
from .paper import Rules, Ledger
from .providers import Client, ProviderError, FRED_SERIES, FED, BLS, bls_events, fed_news, cot, fred, twelve, evidence_file, treasury
from .workflow import Review, snapshot, ROLES
from .mt5_feed import MT5_FRAMES, read_mt5
from .technical import candle_values, scan
from .brokers import BrokerProfiles, PRESETS, broker_command

def options(p):
    p.add_argument("--csv",type=Path,help="spot OHLC CSV with same-stem JSON metadata")
    group=p.add_mutually_exclusive_group()
    group.add_argument("--twelve",choices=list(MT5_FRAMES),help="Twelve Data spot feed; requires TWELVE_DATA_API_KEY")
    group.add_argument("--mt5",choices=list(MT5_FRAMES),help="read gold from an open Windows MT5 terminal")
    p.add_argument("--broker",help="use a saved broker profile; market and prepare use the active profile by default")
    p.add_argument("--mt5-symbol",help="exact broker symbol shown in Market Watch")
    p.add_argument("--mt5-terminal",type=Path,help="path to terminal64.exe if multiple terminals are installed")
    p.add_argument("--mt5-bars",type=int,default=600)
    p.add_argument("--at",type=ts,help="ISO-8601 replay cutoff with timezone")
    p.add_argument("--config",type=Path)
    p.add_argument("--cache",type=Path,default=Path(".gold-cache"))
    p.add_argument("--max-age",type=int,default=10)

def rules(args):
    return Rules(**read_json(args.config)) if args.config else Rules()

def choose_feed(args,at):
    if not 1<=args.max_age<=240:
        raise ValueError("max age must be 1–240 minutes")
    errs=[]
    store=BrokerProfiles()
    selected=args.broker
    if not (selected or args.mt5 or args.csv or args.twelve or args.at) and args.command in {"prepare","market"}:
        selected=store.active()
    if args.mt5 or selected:
        if args.at or args.csv or args.twelve:
            raise ValueError("MT5 is a separate broker feed; do not combine it with --csv, --twelve or --at")
        profile={}
        if selected:
            _,profile=store.get(selected)
        symbol=args.mt5_symbol or profile.get("symbol","XAUUSD")
        frame=args.mt5 or profile["frame"]
        terminal=args.mt5_terminal or (Path(profile["terminal"]) if profile else None)
        feed=read_mt5(symbol,frame,args.mt5_bars,terminal)
        if selected:
            feed.market_meta["broker_profile"]=selected
        return feed,errs
    if args.twelve:
        if args.at:
            raise ValueError("a pinned replay cutoff requires local CSV; latest-vintage feeds are unavailable in replay")
        try:
            f=twelve(Client(args.cache),args.twelve)
            if f.provenance(now(),args.max_age)["fresh"] or not args.csv:
                return f,errs
            errs.append("Twelve Data primary feed stale; attempting CSV fallback")
        except ProviderError as e:
            errs.append(str(e))
    if args.csv:
        try:
            return csv_feed(args.csv,at),errs
        except (ValueError,KeyError,OSError,TypeError):
            errs.append("Local CSV or metadata missing, invalid, or mismatched; verify its schema and timestamps.")
    return None,errs+["No accepted market feed. Run broker setup, use --mt5 or a verified spot CSV, or configure Twelve Data with TWELVE_DATA_API_KEY."]

def acquire(args,at):
    errors=[]
    allrows=[]
    history={}
    if args.public:
        if args.at:
            raise ValueError("public observations cannot be combined with pinned replay time")
        c=Client(args.cache)
        for k in FRED_SERIES:
            try:
                record, series=fred(c,k,at)
                allrows.append(record)
                if k in {"DGS10","DFII10","DTWEXBGS"}:
                    history[k]=series
            except ProviderError as e:
                errors.append(k+": "+str(e))
                if k in {"DGS10","DFII10"}:
                    try:
                        record, series=treasury(c,k,at)
                        allrows.append(record)
                        history[k]=series
                    except ProviderError as f:
                        errors.append(k+" Treasury fallback: "+str(f))
        for name,run in (
            ("CFTC COT",lambda:cot(c,at)),
            ("Federal Reserve monetary news",lambda:c.get(FED,ttl=600,parser=lambda b,t:fed_news(b,t,at))[0]),
            ("BLS calendar",lambda:c.get(BLS,ttl=7200,parser=lambda b,t:bls_events(b,t,at))[0])):
            try:
                rows=run()
                allrows.extend(rows)
                if not rows:
                    errors.append(name+": no validated records")
            except ProviderError as e:
                errors.append(name+": "+str(e))
    allrows+=evidence_file(args.evidence,at)
    present={e["series"] for e in allrows if e["fresh"]}
    for series in sorted({"DXY","COMEX_GOLD_FUTURES","ETF_FLOWS","CENTRAL_BANK_GOLD","PMI","GEOPOLITICS",
                          "LIQUIDITY","FOMC","PCE","GDP"}-present):
        errors.append(series+": no fresh verified event or instrument-specific evidence supplied; see source catalog")
    return allrows,errors,history

def alerts(review,path,above,below,hours):
    if not 1<=hours<=168:
        raise ValueError("alert horizon must be 1–168 hours")
    from .core import num
    if (above is not None and num(above)<=0) or (below is not None and num(below)<=0):
        raise ValueError("threshold must be positive")
    s,w=review.load()
    p=s["provenance"]
    current=ts(s["as_of"])
    messages=[]
    if p and p["fresh"]:
        price=s["technical"][p["frame"]]["last"]
        for name,limit,condition in (("above",above,above is not None and price>=above),
                                     ("below",below,below is not None and price<=below)):
            if condition:
                messages.append((f"{name}:{limit}",f"Latest completed candle is {name} {limit:g} USD/oz ({p['latest_closed_at']})."))
    for e in s["evidence"]+w["followup"]:
        if e["units"]=="event" and current<=ts(e["observed"])<=current+timedelta(hours=hours):
            messages.append((digest([e["instrument"],e["observed"]]),
                             f"Scheduled: {e['instrument']} at {e['observed']} ({e['source']})."))
    data=read_json(path) if path.exists() else {}
    active={k:current.isoformat() for k,_ in messages if k.startswith(("above:","below:"))}
    emitted=[]
    # A threshold can ring after it first resets; events ring once within the 30-day retention.
    seen={k:v for k,v in data.items() if not k.startswith(("above:","below:")) and ts(v)>=current-timedelta(days=30)}
    for k,m in messages:
        if k not in data:
            emitted.append(m)
        if k not in active:
            seen[k]=current.isoformat()
    write_json(path,seen|active)
    return emitted

def prepare(args):
    at=args.at or now()
    rows,errs,history=acquire(args,at)
    f,errors=choose_feed(args,args.at or now())
    if not args.at:
        at=max(now(),f.retrieved_at) if f and f.instrument==MT5_GOLD else now()
    holidays=read_json(args.holidays) if args.holidays else {}
    from datetime import date
    for day,flag in holidays.items():
        date.fromisoformat(day)
        if flag!="closed" and not (type(flag) is int and 0<=flag<=23):
            raise ValueError("holiday override must be 'closed' or a New York close hour")
    s=snapshot(f,at,args.mode,rules(args),rows,errors+errs,args.max_age,holidays,history)
    review=Review(args.session)
    review.start(s,args.method)
    review.report()
    return {"session":str(args.session),"method":args.method,"provenance":s["provenance"],
            "data_limitations":s["gaps_and_errors"],"workflow":str(review.track)}

def market(args):
    if not 1<=args.recent<=100:
        raise ValueError("--recent must be 1–100")
    at=args.at or now()
    feed,errs=choose_feed(args,at)
    if not feed:
        raise ValueError("; ".join(errs))
    at=args.at or (max(now(),feed.retrieved_at) if feed.instrument==MT5_GOLD else now())
    p=feed.provenance(at,args.max_age)
    if args.require_demo and p.get("account_mode") != "demo":
        raise ValueError("MT5 account is not confirmed as demo; check the account selected in the terminal")
    if args.require_fresh and (not p["fresh"] or p["synthetic"]):
        raise ValueError("completed market candles are stale, missing or synthetic")
    bars=feed.closed(at)
    data={"provenance":p,"indicators":scan(bars),"candles":[candle_values(b) for b in bars[-args.recent:]],
          "provider_warnings":errs}
    if args.out:
        write_json(args.out,data)
    if args.log:
        import json
        args.log.parent.mkdir(parents=True,exist_ok=True)
        with args.log.open("a",encoding="utf-8") as log:
            log.write(json.dumps(data,allow_nan=False)+"\n")
    return data

def paper_step(args):
    if args.mt5 or args.broker:
        raise ValueError("MT5 broker data is research only; the paper simulator requires spot mid or indicative data")
    at=args.at or now()
    feed,errs=choose_feed(args,at)
    if not feed:
        raise ValueError("; ".join(errs))
    if not args.at:
        at=now()
    plan=None
    if args.queue:
        s=snapshot(feed,at,"quick",rules(args),[],[],args.max_age,{})
        plan=s["paper_hypothesis"]
        if not plan:
            raise ValueError("no eligible current hypothetical breakout; run without --queue to advance the ledger")
    return Ledger(args.db).apply(rules(args),feed,at,plan,args.max_age)|{"provider_warnings":errs}

def create_parser():
    p=argparse.ArgumentParser(prog="python -m gold_desk",description="XAUUSD research and virtual-only simulation")
    sub=p.add_subparsers(dest="command",required=True)
    b=sub.add_parser("broker",help="set up and switch saved local MT5 profiles")
    b.set_defaults(run=broker_command)
    bs=b.add_subparsers(dest="action",required=True)
    bs.add_parser("list",help="list presets and saved profiles")
    q=bs.add_parser("paths",help="list installed MT5 paths for a preset")
    q.add_argument("preset",choices=PRESETS)
    q=bs.add_parser("setup",help="save and activate a broker profile")
    q.add_argument("preset",choices=PRESETS)
    q.add_argument("--terminal",type=Path,help="path to the broker's terminal64.exe")
    q.add_argument("--symbol",default="XAUUSD")
    q.add_argument("--frame",choices=MT5_FRAMES,default="5m")
    q.add_argument("--name",help="optional custom name for another install or account profile")
    q=bs.add_parser("use",help="set the active broker")
    q.add_argument("name")
    q=bs.add_parser("show",help="display a saved profile (defaults to active)")
    q.add_argument("name",nargs="?")
    q=sub.add_parser("market",help="read candles, wicks and indicators into JSON")
    options(q)
    q.add_argument("--recent",type=int,default=12)
    q.add_argument("--require-fresh",action="store_true")
    q.add_argument("--require-demo",action="store_true",help="require MT5 to report a demo account")
    q.add_argument("--log",type=Path,help="append timestamped market snapshot as JSONL")
    q.add_argument("--out",type=Path)
    q.set_defaults(run=market)
    q=sub.add_parser("prepare",help="prepare frozen evidence and report")
    options(q)
    q.add_argument("--session",type=Path,required=True)
    q.add_argument("--public",action="store_true")
    q.add_argument("--evidence",type=Path)
    q.add_argument("--holidays",type=Path)
    q.add_argument("--mode",choices=["quick","standard","deep"],default="standard")
    q.add_argument("--method",choices=["native-host","sequential-role-fallback","offline-no-agents"],
                   default="offline-no-agents")
    q.set_defaults(run=prepare)
    for action in ("status","packet","submit","followup","report","alerts"):
        q=sub.add_parser(action)
        q.add_argument("--session",type=Path,required=True)
        if action in {"packet","submit"}:
            q.add_argument("role",choices=ROLES)
        if action in {"submit","followup"}:
            q.add_argument("file",type=Path)
        if action in {"report","alerts"}:
            q.add_argument("--db",type=Path)
        if action=="alerts":
            q.add_argument("--above",type=float)
            q.add_argument("--below",type=float)
            q.add_argument("--hours",type=int,default=24)
            q.add_argument("--state",type=Path,default=Path(".gold-alerts.json"))
        q.set_defaults(run=route)
    q=sub.add_parser("paper-step",help="advance or queue a virtual hypothesis")
    options(q)
    q.add_argument("--db",type=Path,required=True)
    q.add_argument("--queue",action="store_true")
    q.set_defaults(run=paper_step)
    q=sub.add_parser("account")
    q.add_argument("--db",type=Path,required=True)
    q.set_defaults(run=lambda x: Ledger(x.db).summary())
    return p

def route(a):
    r=Review(a.session)
    cmd=a.command
    if cmd=="status":
        s,w=r.load()
        phase=r.current(s,w)
        return {"phase":phase,"pending":[role for role in r.phases(s).get(phase,[])
                         if role not in w["submissions"].get(phase,{})],"method":w["method"]}
    if cmd=="packet":
        return r.packet(a.role)
    if cmd=="submit":
        r.submit(a.role,a.file)
        return {"recorded":a.role}
    if cmd=="followup":
        r.add_followup(a.file)
        return {"recorded":"follow-up evidence"}
    if cmd=="alerts":
        out=alerts(r,a.state,a.above,a.below,a.hours)
        r.report(Ledger(a.db).summary() if a.db else None,out)
        return {"alerts":out}
    d=r.report(Ledger(a.db).summary() if a.db else None)
    return {"conclusion":d["research_conclusion"],"Markdown":str(a.session/"report.md"),
            "JSON":str(a.session/"report.json")}

def main(argv=None):
    a=create_parser().parse_args(argv)
    try:
        print(json_text(a.run(a)))
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as e:
        print(f"Research desk: {e}",file=sys.stderr)
        return 2
    return 0
