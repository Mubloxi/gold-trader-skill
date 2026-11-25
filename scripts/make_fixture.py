"""Generate an explicitly synthetic 5-minute OHLC fixture. No market data."""
from datetime import datetime, timedelta, timezone
import csv
import json
import math
from pathlib import Path
from random import Random

def generate(path):
    start=datetime(2025,1,6,0,0,tzinfo=timezone.utc)
    rng=Random(936)
    last=2650.
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        out=csv.writer(f,lineterminator="\n")
        out.writerow(["close_time","open","high","low","close"])
        for i in range(1,1101):
            stamp=start+timedelta(minutes=5*i)
            drift=.25 if (i//36)%2==0 else -.25
            jump=(1.5 if (i//36)%2==0 else -1.5) if i%36==15 else 0.
            close=last+3*(drift+math.sin(i/11)*.18+rng.uniform(-.14,.14)+jump)
            high=max(last,close)+rng.uniform(.33,.84)
            low=min(last,close)-rng.uniform(.33,.84)
            out.writerow([stamp.isoformat().replace("+00:00","Z"),*[f"{v:.5f}" for v in (last,high,low,close)]])
            last=close
    path.with_suffix(".json").write_text(json.dumps({
      "instrument":"XAUUSD_SPOT","frame":"5m","quote_kind":"mid","synthetic":True,
      "delay":"synthetic; no market feed","source":"fixture:deterministic-gold-like-candles"
    },indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    generate(Path(__file__).resolve().parent.parent/"tests/fixtures/synthetic-gold.csv")
