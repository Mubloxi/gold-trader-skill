"""Reproduce report and virtual ledger offline from the bundled synthetic dataset."""
from pathlib import Path
from argparse import ArgumentParser
from datetime import timedelta
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from gold_desk.cli import main
from gold_desk.core import csv_feed, iso, ts, read_json, write_json
from gold_desk.paper import make_plan

def run(out):
    if out.exists() and any(out.iterdir()):
        raise ValueError("demo output must be empty or a new directory")
    out.mkdir(parents=True,exist_ok=True)
    f=ROOT/"tests/fixtures/synthetic-gold.csv"
    bars=csv_feed(f,ts("2025-01-10T00:00:00Z")).bars
    i=next(i for i in range(260,len(bars)-24) if make_plan(bars[max(0,i-60):i+1]))
    db=str(out/"virtual.sqlite")
    session=str(out/"research")
    examples=[["paper-step","--csv",str(f),"--db",db,"--queue","--at",iso(bars[i].close_time)],
              ["paper-step","--csv",str(f),"--db",db,"--at",iso(bars[i+24].close_time)],
              ["prepare","--csv",str(f),"--at",iso(bars[-1].close_time),"--session",session,"--mode","deep"],
              ["report","--session",session,"--db",db]]
    for cmd in examples:
        result=main(cmd)
        if result:
            return result
    report=read_json(Path(session)/"report.json")
    history=report["paper_account"]["history"]
    if not any(x["type"]=="close" for x in history):
        raise ValueError("demo did not exercise the paper close path")
    write_json(out/"demo-summary.json",{
        "fixture":"SYNTHETIC","research_conclusion":report["research_conclusion"],
        "research_execution":report["research_execution"],
        "virtual_account":report["paper_account"]["account"]["state"],
        "events":[x["type"] for x in history],"forward_folds":len(report["simulation"]["test_folds"])})
    return 0

if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path("demo-run"))
    a=p.parse_args()
    raise SystemExit(run(a.out))
