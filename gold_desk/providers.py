"""GET-only provider adapters; responses are untrusted and credentials stay out of cache keys."""
from datetime import timedelta, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
from pathlib import Path
import csv
import io
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from .core import Bar, Feed, SPOT, FRAMES, UTC, now, ts, iso, num, https, digest, read_json, write_json

FRED_SERIES = {
    "DGS10":("US Treasury 10-year nominal yield","percent",7),
    "DFII10":("US Treasury 10-year real yield","percent",7),
    "DTWEXBGS":("Fed broad trade-weighted dollar index (not DXY)","index",14),
    "CPIAUCSL":("Headline CPI, seasonally adjusted","index",50),
    "PPIACO":("Producer price index, all commodities","index",55),
    "PCEPI":("Headline PCE price index","index",75),
    "PAYEMS":("Total nonfarm payrolls, seasonally adjusted","thousands of jobs",55),
    "GDPC1":("Real US GDP","billions of chained 2017 USD at SAAR",160),
    "DFEDTARU":("Federal funds target range upper bound","percent",7),
}
CFTC = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
BLS = "https://www.bls.gov/schedule/news_release/bls.ics"
FED = "https://www.federalreserve.gov/feeds/press_monetary.xml"
TWELVE = "https://api.twelvedata.com/time_series"
HOSTS = {"fred.stlouisfed.org","publicreporting.cftc.gov","www.bls.gov",
         "www.federalreserve.gov","api.twelvedata.com","home.treasury.gov"}
MANUAL = {"DXY","COMEX_GOLD_FUTURES","ETF_FLOWS","CENTRAL_BANK_GOLD","PMI","GEOPOLITICS",
          "LIQUIDITY","FOMC","CPI","PPI","PCE","PAYROLLS","GDP","NEWS"}

class ProviderError(ValueError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Client:
    def __init__(self,cache,transport=None,clock=now,pause=time.sleep):
        self.cache=Path(cache)
        self.transport=transport or self._request
        self.clock=clock
        self.pause=pause
        self.last={}
        self.deadline=time.monotonic()+65

    @staticmethod
    def _request(url,headers):
        with build_opener(NoRedirect()).open(Request(url, headers=headers,method="GET"),timeout=6) as r:
            raw=r.read(6_000_001)
        if len(raw)>6_000_000:
            raise ProviderError("response too large")
        return raw.decode("utf-8-sig")

    def get(self,url,params=None,ttl=900,authorization=None,parser=lambda body,at: body):
        host=urlsplit(https(url)).hostname
        if host not in HOSTS or urlsplit(url).port not in (None,443) or urlsplit(url).query:
            raise ProviderError("unexpected provider URL")
        headers={"User-Agent":"XAUUSD-Research-Desk/1.0 (public-data research)"}
        if authorization:
            headers["Authorization"]=authorization
        path=self.cache/(digest([url,params or {},digest(authorization) if authorization else "public"])+".json")
        current=self.clock()
        try:
            cached=read_json(path)
            at=ts(cached["retrieved_at"])
            if 0 <= (current-at).total_seconds() < ttl:
                return parser(cached["body"],at), at
        except (OSError,ValueError,TypeError,KeyError):
            pass
        for i in range(3):
            if time.monotonic()>=self.deadline:
                raise ProviderError("network research budget exhausted")
            wait=self.last.get(host,0)+0.55-time.monotonic()
            if wait>0:
                self.pause(wait)
            self.last[host]=time.monotonic()
            try:
                body=self.transport(url+("?"+urlencode(params) if params else ""),headers)
                at=self.clock()
                result=parser(body,at)
                write_json(path,{"body":body,"retrieved_at":iso(at)})
                return result,at
            except HTTPError as e:
                if e.code!=429 and not 500<=e.code<=599:
                    raise ProviderError(f"{host}: HTTP {e.code}") from None
                if i<2:
                    retry=e.headers.get("Retry-After","") if e.headers else ""
                    if retry.isdigit() and int(retry)>10:
                        raise ProviderError(f"{host}: rate limited; retry later") from None
                    self.pause(max(2**i,int(retry)) if retry.isdigit() else 2**i)
            except (URLError, TimeoutError):
                if i<2:
                    self.pause(2**i)
            except (KeyError,TypeError,AttributeError,ValueError,ET.ParseError) as e:
                raise ProviderError(f"{host}: invalid response ({type(e).__name__})") from None
        raise ProviderError(f"{host}: request failed after bounded retries")

def parse_twelve(body,at,frame):
    d=json.loads(body)
    if d.get("status")=="error" or d["meta"]["symbol"]!="XAU/USD":
        raise ProviderError("missing or incorrect Twelve Data instrument")
    if d["meta"].get("interval") != {"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h"}[frame]:
        raise ProviderError("unexpected Twelve Data interval")
    rows=[]
    for x in d["values"]:
        stamp=ts(x["datetime"].replace(" ","T")+("Z" if len(x["datetime"])==19 else ""))
        rows.append(Bar(stamp+timedelta(minutes=FRAMES[frame]),*(num(x[k]) for k in ("open","high","low","close"))))
    return Feed(sorted(rows,key=lambda b:b.close_time),frame,"https://twelvedata.com/symbols/commodity/xau-usd",
                at,SPOT,"indicative","provider entitlement and latency unverified")

def twelve(client,frame):
    frames={"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h"}
    key=os.getenv("TWELVE_DATA_API_KEY")
    if not key or not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}",key):
        raise ProviderError("Twelve Data key missing or invalid")
    if frame not in frames:
        raise ProviderError("unsupported provider timeframe")
    return client.get(TWELVE,{"symbol":"XAU/USD","interval":frames[frame],"timezone":"UTC",
                              "outputsize":"1000"},ttl=60,authorization="apikey "+key,
                      parser=lambda body,at:parse_twelve(body,at,frame))[0]

def observation(series,label,value,units,observed,retrieved,source,as_of,max_age,availability=None):
    date=datetime.fromisoformat(observed[:10]).date()
    age=(as_of.date()-date).days
    return {"series":series,"instrument":label,"value":value,"units":units,"source":https(source),
            "observed":observed,"retrieved_at":iso(retrieved),"age_days":age,
            "fresh":0<=age<=max_age,"available_at":availability}

def fred(client,series,as_of):
    label,units,max_age=FRED_SERIES[series]
    def parse(body,at):
        out={}
        r=csv.DictReader(io.StringIO(body))
        if series not in (r.fieldnames or []):
            raise ProviderError("missing FRED series column")
        for row in r:
            date=row.get("observation_date",row.get("DATE"))
            date=datetime.fromisoformat(date).date().isoformat()
            if date <= min(at,as_of).date().isoformat() and row[series] not in (".",""):
                out[date]=num(row[series])
        if not out:
            raise ProviderError("no usable FRED values")
        latest=max(out)
        record=observation(series,label,out[latest],units,latest,at,
                           "https://fred.stlouisfed.org/series/"+series,as_of,max_age)
        dates=sorted(out)
        if len(dates)>1:
            prior=dates[-2]
            record["previous_observation"]={"date":prior,"value":out[prior],"change_native_units":out[latest]-out[prior]}
        if series in {"CPIAUCSL","PCEPI","PPIACO"}:
            day=datetime.fromisoformat(latest).date()
            previous_year=day.replace(year=day.year-1).isoformat()
            if previous_year in out and out[previous_year]>0:
                record["year_over_year_percent"]=100*(out[latest]/out[previous_year]-1)
        return record,out
    return client.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                      {"id":series,"cosd":(as_of.date()-timedelta(days=720)).isoformat()},14400,
                      parser=parse)[0]

def cot(client,as_of):
    fields="report_date_as_yyyy_mm_dd,cftc_contract_market_code,m_money_positions_long_all,m_money_positions_short_all,open_interest_all"
    def parse(body,at):
        results=[]
        for row in json.loads(body):
            if row["cftc_contract_market_code"]!="088691":
                raise ProviderError("wrong CFTC instrument")
            day=row["report_date_as_yyyy_mm_dd"][:10]
            if day>as_of.date().isoformat():
                continue
            l,s,oi=[int(row[x]) for x in fields.split(",")[2:]]
            if min(l,s)<0 or oi<=0 or max(l,s)>oi:
                raise ProviderError("invalid CFTC positions")
            results.append(observation("COT_COMEX_088691","COMEX gold futures: managed money",{"long":l,"short":s,"net":l-s,"open_interest":oi},
                          "contracts",day,at,"https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy",as_of,14))
        if not results:
            raise ProviderError("no gold COT records")
        return sorted(results,key=lambda x:x["observed"],reverse=True)
    return client.get(CFTC,{"$where":"cftc_contract_market_code='088691'","$select":fields,
                            "$order":"report_date_as_yyyy_mm_dd DESC","$limit":12},21600,parser=parse)[0]

def bls_events(body,at,as_of):
    if not body.lstrip().startswith("BEGIN:VCALENDAR"):
        raise ProviderError("expected iCalendar")
    lines=re.sub(r"\r?\n[ \t]","",body)
    results=[]
    for block in lines.split("BEGIN:VEVENT")[1:]:
        block=block.split("END:VEVENT")[0]
        match=re.search(r"^DTSTART(?P<params>[^:]*):(?P<when>\d{8}T\d{6}Z?)\s*$",block,re.M)
        title=re.search(r"^SUMMARY(?:;[^:]*)?:(.*)$",block,re.M)
        if not match or not title:
            continue
        when=match["when"]
        if not when.endswith("Z") and not re.search(r"TZID=(America/New_York|US/Eastern)",match["params"]):
            continue
        d=datetime.strptime(when.rstrip("Z"),"%Y%m%dT%H%M%S").replace(
            tzinfo=UTC if when.endswith("Z") else ZoneInfo("America/New_York"))
        if as_of-timedelta(days=3)<=d<=as_of+timedelta(days=30):
            results.append({"series":"BLS_CALENDAR","instrument":title[1].strip()[:160],
              "value":"scheduled","units":"event","source":BLS,"observed":iso(d),
              "retrieved_at":iso(at),"available_at":iso(at),"fresh":True})
    if not results:
        raise ProviderError("no supported dated BLS events in window")
    return results

def fed_news(body,at,as_of):
    if "<!DOCTYPE" in body.upper() or "<!ENTITY" in body.upper():
        raise ProviderError("RSS declarations forbidden")
    root=ET.fromstring(body)
    if root.tag!="rss":
        raise ProviderError("expected RSS")
    rows=[]
    for item in root.findall("./channel/item")[:40]:
        p=parsedate_to_datetime(item.findtext("pubDate",""))
        if p.tzinfo is None or not as_of-timedelta(days=14)<=p<=min(as_of,at):
            continue
        rows.append({"series":"NEWS","instrument":item.findtext("title","").strip()[:160],
           "value":"headline only","units":"headline","source":https(item.findtext("link","").strip()),
           "observed":iso(p),"retrieved_at":iso(at),"available_at":iso(p),"fresh":True})
    return rows

def evidence_file(path,as_of):
    if path is None:
        return []
    rows=read_json(path)
    if not isinstance(rows,list) or len(rows)>200:
        raise ValueError("expected at most 200 manual evidence records")
    clean=[]
    for r in rows:
        kind=r["series"]
        if kind not in MANUAL:
            raise ValueError("unknown manual series")
        src=https(r["source"])
        event=ts(r["observed"])
        avail=ts(r["available_at"])
        retr=ts(r["retrieved_at"])
        if avail>min(as_of,retr) or retr>as_of:
            raise ValueError("manual evidence unavailable at research cutoff")
        if event>as_of and r["units"]!="event":
            raise ValueError("future observation must be a scheduled event")
        value=r["value"]
        if isinstance(value,str):
            value=value.strip()[:600]
        else:
            value=num(value)
        age=(as_of-event).total_seconds()/86400
        clean.append({"series":kind,"instrument":str(r["instrument"])[:160],"value":value,
             "units":str(r["units"])[:50],"source":src,"observed":iso(event),"retrieved_at":iso(retr),
             "available_at":iso(avail),"age_days":round(age,4),
             "fresh":-30<=age<=({"COT":14,"ETF_FLOWS":14,"CENTRAL_BANK_GOLD":100,"PMI":45}.get(kind,7)),
             "manual_unverified":True})
    return clean

def dedupe(rows):
    result={}
    headlines=set()
    for r in rows:
        key=(r["series"],r["source"].split("?")[0],r["observed"] if r["units"]!="headline" else "")
        title=re.sub(r"\W+"," ",r["instrument"].casefold()).strip()
        if key in result or (r["units"]=="headline" and title in headlines):
            continue
        result[key]=r
        if r["units"]=="headline":
            headlines.add(title)
    return list(result.values())

TREASURY = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"

def treasury(client,series,as_of):
    if series not in {"DGS10","DFII10"}:
        raise ProviderError("unsupported Treasury fallback")
    curve="daily_treasury_yield_curve" if series=="DGS10" else "daily_treasury_real_yield_curve"
    field="BC_10YEAR" if series=="DGS10" else "TC_10YEAR"
    label,units,max_age=FRED_SERIES[series]
    def parse(body,at):
        if "<!DOCTYPE" in body.upper() or "<!ENTITY" in body.upper():
            raise ProviderError("XML declarations forbidden")
        root=ET.fromstring(body)
        result={}
        for props in root.findall(".//{*}properties"):
            raw=props.findtext("{*}NEW_DATE")
            val=props.findtext("{*}"+field)
            if raw and val and raw[:10]<=min(as_of,at).date().isoformat():
                result[datetime.fromisoformat(raw).date().isoformat()]=num(val)
        if not result:
            raise ProviderError("no matching Treasury par rates")
        latest=max(result)
        return observation(series,label,result[latest],units,latest,at,
                     "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed",as_of,max_age),result
    return client.get(TREASURY,{"data":curve,"field_tdr_date_value":str(as_of.year)},14400,parser=parse)[0]
