"""Bounded schemas and deterministic persistence utilities."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import tempfile
from urllib.parse import parse_qsl, urlsplit

UTC = timezone.utc
FRAMES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
SPOT = "XAUUSD_SPOT"
MT5_GOLD = "XAUUSD_MT5_BROKER"

def now():
    return datetime.now(UTC).replace(microsecond=0)

def ts(s):
    if not isinstance(s,str):
        raise ValueError("expected timestamp string")
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.utcoffset() is None:
        raise ValueError("explicit timezone required")
    return d.astimezone(UTC)

def iso(d):
    if d.utcoffset() is None:
        raise ValueError("explicit timezone required")
    return d.astimezone(UTC).isoformat().replace("+00:00", "Z")

def num(x):
    if isinstance(x, bool) or not math.isfinite(v := float(x)):
        raise ValueError("expected finite number")
    return v

def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)

def digest(data):
    return hashlib.sha256(json_text(data).encode()).hexdigest()

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp = f.name
        try:
            f.write(data + "\n")
            f.flush()
            os.fsync(f.fileno())
            f.close()
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

def write_json(path, data):
    write(path, json_text(data))

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def https(url):
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("expected HTTPS source with no credentials")
    if any(k.casefold().replace("-", "_") in {"apikey","api_key","access_token","token","signature","x_amz_signature",
                                              "key","sig","password","secret","auth","authorization"}
           for k,_ in parse_qsl(p.query,keep_blank_values=True,max_num_fields=100)):
        raise ValueError("source URL must not contain secrets")
    return url

@dataclass(frozen=True)
class Bar:
    close_time: datetime
    o: float
    h: float
    l: float
    c: float

    def __post_init__(self):
        if self.close_time.utcoffset() is None:
            raise ValueError("bar timestamp must have a timezone")
        o,h,l,c = map(num, (self.o,self.h,self.l,self.c))
        if not 0 < l <= min(o,c) <= max(o,c) <= h:
            raise ValueError("invalid OHLC envelope")
        object.__setattr__(self,"close_time",self.close_time.astimezone(UTC))
        for k,v in zip(("o","h","l","c"),(o,h,l,c)):
            object.__setattr__(self,k,v)

    def record(self):
        return asdict(self) | {"close_time": iso(self.close_time)}

def ordered(bars, frame):
    step = FRAMES[frame] * 60
    if not bars or len(bars) > 200_000:
        raise ValueError("expected 1–200,000 bars")
    for i,b in enumerate(bars):
        if b.close_time.timestamp() % step or (i and bars[i-1].close_time >= b.close_time):
            raise ValueError("bars must be unique, increasing and aligned to UTC grid")
    return bars

@dataclass
class Feed:
    bars: list
    frame: str
    source: str
    retrieved_at: datetime
    instrument: str = SPOT
    quote_kind: str = "indicative"
    delay: str = "unverified"
    synthetic: bool = False
    market_meta: dict | None = None

    def __post_init__(self):
        ordered(self.bars, self.frame)
        if (self.instrument == SPOT and self.quote_kind not in {"mid","bid","ask","indicative"}) or (
                self.instrument == MT5_GOLD and self.quote_kind not in {"bid","last","unknown"}) or (
                self.instrument not in {SPOT,MT5_GOLD}):
            raise ValueError("expected gold candles with declared instrument and quote basis")
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieval time needs timezone")
        if not self.synthetic:
            https(self.source)

    def closed(self, as_of):
        return [b for b in self.bars if b.close_time <= min(as_of, self.retrieved_at)]

    def provenance(self, as_of, max_age_minutes=10):
        bars = self.closed(as_of)
        latest = bars[-1].close_time if bars else None
        age = (as_of-latest).total_seconds() if latest else None
        meta = {}
        if self.market_meta:
            meta = dict(self.market_meta)
            if quote := meta.get("last_quote"):
                seconds = (as_of-ts(quote["at"])).total_seconds()
                meta["last_quote"] = quote | {"age_seconds":seconds,"fresh":0<=seconds<=max_age_minutes*60} if seconds>=0 else None
        return {"source":self.source,"instrument":self.instrument,"units":"USD/troy oz",
                "retrieved_at":iso(self.retrieved_at),"latest_closed_at":iso(latest) if latest else None,
                "age_seconds":age,"fresh":age is not None and age <= max_age_minutes*60,
                "frame":self.frame,"delay":self.delay,"quote_kind":self.quote_kind,
                "synthetic":self.synthetic} | meta

def csv_feed(path, as_of):
    path = Path(path)
    meta = read_json(path.with_suffix(".json"))
    if meta["instrument"] != SPOT:
        raise ValueError("CSV importer accepts spot XAU/USD only")
    if not isinstance(meta.get("synthetic",False),bool):
        raise ValueError("synthetic must be boolean")
    if "retrieved_at" not in meta and not meta.get("synthetic",False):
        raise ValueError("record the actual retrieval time of non-synthetic data")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(f)
        if rows.fieldnames != ["close_time","open","high","low","close"]:
            raise ValueError("unexpected OHLC CSV header")
        bars = []
        for row in rows:
            if len(bars) == 200_000:
                raise ValueError("too many bars")
            bars.append(Bar(ts(row["close_time"]), *(num(row[k]) for k in ("open","high","low","close"))))
    return Feed(bars,meta["frame"],meta["source"],ts(meta.get("retrieved_at",iso(as_of))),
                meta["instrument"],meta["quote_kind"],meta["delay"],meta.get("synthetic",False))
