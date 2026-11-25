"""Evidence packets, genuine host submissions and reproducible reports."""
from pathlib import Path
import json
import re
from datetime import timedelta
from .core import digest, iso, num, read_json, ts, write, write_json, json_text
from .providers import dedupe, evidence_file
from .technical import resample, scan, session_info, session_levels, aligned_correlation
from .paper import make_plan
from .replay import walk_forward

ROLES={
 "technical-scanner":"Summarize calculated bars, structure and liquidity limitations. Do not estimate indicators.",
 "news-intelligence":"Rank verified, deduplicated macro and geopolitical developments; separate facts from causal hypotheses.",
 "entry-researcher":"Check freshness and completed-bar conditions for a hypothetical setup. No personal or broker recommendations.",
 "exit-researcher":"Explain invalidation and modeled execution uncertainty; review stops, target ambiguity, gaps and expiry.",
 "time-machine":"Review holdouts, costs, regimes, sample size and bootstrap assumptions without extrapolating returns.",
 "risk-manager":"Independently identify veto conditions and costs. You cannot grant or override the Python veto.",
 "budget-manager":"Read virtual account exposure and sizing assumptions only; never suggest a funded position.",
 "paper-broker":"Review simulation and modeled fills; never connect an external broker or submit orders.",
 "alert-manager":"Report price conditions and upcoming sourced events with timezones and confirmation status.",
 "macro-analyst":"Assess Fed policy, inflation, labor, GDP, PMI, nominal/real yields and USD; test rather than assume relationships.",
 "institutional-analyst":"Compare dated CFTC futures positions, ETF and central-bank demand; distinguish observation and publication.",
 "bull-researcher":"Develop strongest plausible gold upside thesis. Include evidence against it and falsification conditions.",
 "bear-researcher":"Develop strongest plausible gold downside thesis. Include evidence against it and falsification conditions.",
 "independent-critic":"Find conflicting claims, stale and missing evidence, data leakage, costs, and overfitting; request evidence as warranted.",
 "research-director":"Synthesize competing views; preserve unresolved objections. Never synthesize fake agent submissions or override risk."
}
FIRST={
 "quick":["bull-researcher","bear-researcher","risk-manager"],
 "standard":["bull-researcher","bear-researcher","risk-manager","technical-scanner","news-intelligence","macro-analyst","institutional-analyst"],
 "deep":[k for k in ROLES if k not in {"independent-critic","research-director"}]
}
PHASES=("independent","cross","critique","revision","decision")
PHASE_TASK={
 "independent":"Reason from the snapshot alone; state material limitations and what would change your view.",
 "cross":"Challenge specific opposing claims, identify where you agree, and ask for missing evidence. Do not force agreement.",
 "critique":"Audit the claims and counterclaims for contradictions, data lag, missing evidence, overfitting and execution assumptions.",
 "revision":"Address critiques and follow-up evidence; explicitly retain, revise or retract your independent thesis.",
 "decision":"Resolve what the evidence supports, record unresolved dissent, and use one of the declared conclusions."}
DECISIONS={"bullish","bearish","neutral","insufficient evidence","no simulated trade"}

def snapshot(feed,as_of,mode,rules,rows,errors,max_age,holidays,macro_series=None):
    technical={}
    gaps=None
    bar_provenance=None
    proposed=None
    tests={"status":"not run"}
    corr={}
    if feed:
        from .core import FRAMES
        bars=feed.closed(as_of)
        bar_provenance=feed.provenance(as_of,max_age)
        step=timedelta(minutes=FRAMES[feed.frame])
        gaps=sum(b.close_time-a.close_time!=step for a,b in zip(bars,bars[1:]))
        technical[feed.frame]=scan(bars)
        for f in ("15m","1h","4h"):
            if FRAMES[f]>FRAMES[feed.frame] and FRAMES[f]%FRAMES[feed.frame]==0:
                technical[f]=scan(resample(bars,feed.frame,f))
        technical["session_levels"]=session_levels(bars,holidays,feed.frame)
        if mode!="quick" and feed.quote_kind in {"mid","indicative"}:
            tests=walk_forward(bars,feed.frame,rules,folds=3 if mode=="standard" else 5,
                               samples=1000 if mode=="standard" else 3000)
        if bars and bar_provenance["fresh"] and feed.quote_kind in {"mid","indicative"}:
            proposed=make_plan(bars[-61:]) if len(bars)>=21 and all(
                b.close_time-a.close_time==step for a,b in zip(bars[-22:-1],bars[-21:])) else None
        # Only the 22:00 UTC sampled spot price, matched by UTC date, never a close-of-day claim.
        close={b.close_time.date().isoformat():b.c for b in bars if b.close_time.hour==22 and b.close_time.minute==0}
        corr={k:aligned_correlation(close,v) for k,v in (macro_series or {}).items()}
    normalized=[]
    for r in dedupe(rows):
        normalized.append(r|{"id":"E-"+digest(r)[:16]})
    if bar_provenance:
        pr=bar_provenance
        b={"series":"SPOT_OHLC","units":pr["units"],"instrument":pr["instrument"],
           "value":f"Completed {feed.frame} bars; {gaps} discontinuities; {pr['delay']}",
           "source":pr["source"],"observed":pr["latest_closed_at"],"retrieved_at":pr["retrieved_at"],
           "fresh":pr["fresh"],"age_seconds":pr["age_seconds"],"synthetic":pr["synthetic"]}
        normalized.append(b|{"id":"E-"+digest(b)[:16]})
    return {"as_of":iso(as_of),"mode":mode,"instrument":"XAUUSD spot, indicative USD/troy oz",
            "provenance":bar_provenance,"gaps":gaps,"technical":technical,
            "sessions":session_info(as_of,holidays),"evidence":normalized,
            "price_yield_dollar_correlation":corr,"simulation":tests,"paper_hypothesis":proposed,
            "risk_floor":{"eligible_hypothesis":bool(proposed),
                          "note":"No paper fill approved. Independent ledger veto runs at simulated execution."},
            "gaps_and_errors":errors}

class Review:
    def __init__(self,path):
        self.root=Path(path)
        self.base=self.root/"snapshot.json"
        self.track=self.root/"workflow.json"

    def start(self,s,method):
        if self.base.exists() or self.track.exists():
            raise ValueError("session already exists; use a new session directory")
        if method not in {"native-host","sequential-role-fallback","offline-no-agents"}:
            raise ValueError("invalid execution method")
        write_json(self.base,s)
        write_json(self.track,{"version":1,"snapshot_digest":digest(s),
            "method":method,"submissions":{},"followup":[]})

    def load(self):
        s,w=read_json(self.base),read_json(self.track)
        if digest(s)!=w["snapshot_digest"]:
            raise ValueError("evidence snapshot integrity mismatch")
        return s,w

    def phases(self,s):
        return {"independent":FIRST[s["mode"]],"cross":["bull-researcher","bear-researcher"],
                "critique":["independent-critic"],"revision":["bull-researcher","bear-researcher"],
                "decision":["research-director"]}

    def current(self,s,w):
        if w["method"]=="offline-no-agents":
            return None
        return next((p for p,r in self.phases(s).items()
                     if any(k not in w["submissions"].get(p,{}) for k in r)),None)

    def packet(self,role):
        s,w=self.load()
        phase=self.current(s,w)
        if not phase or role not in self.phases(s)[phase] or role in w["submissions"].get(phase,{}):
            raise ValueError("role is not pending in the current phase")
        earlier={}
        if phase!="independent":
            earlier={k:v for k,v in w["submissions"].items() if PHASES.index(k)<PHASES.index(phase)}
        sim=s["simulation"]
        # Full deterministic metrics remain in snapshot/report; agents read summary slices by default.
        sim_short={k:v for k,v in sim.items() if k!="test_folds"}
        if "test_folds" in sim:
            sim_short["folds"]=[{"training_end":f["training_end"],"selected_lookback":f["selected_lookback"],
               "out_of_sample":{k:v for k,v in f["out_of_sample"].items() if k not in
                  {"trade_pnl","loss_distribution","win_distribution"}}} for f in sim["test_folds"]]
        context={k:s[k] for k in ("as_of","instrument","technical","provenance","sessions","risk_floor","gaps_and_errors")}
        context["simulation"]=sim_short
        context["evidence"]=s["evidence"]+w["followup"]
        return {"role":role,"phase":phase,"task":ROLES[role],"stage_instruction":PHASE_TASK[phase],"snapshot_digest":w["snapshot_digest"],
                "untrusted_data":context,"previous_phase_submissions":earlier,"method":w["method"]}

    def submit(self,role,path):
        packet=self.packet(role)
        if Path(path).stat().st_size>25_000:
            raise ValueError("agent submission too large")
        v=read_json(path)
        if not isinstance(v,dict) or set(v)-{"role","phase","snapshot_digest","claims","questions","revision","decision","usage","host_run_id"}:
            raise ValueError("unexpected submission schema")
        for k in ("role","phase","snapshot_digest"):
            if v.get(k)!=packet[k]:
                raise ValueError("submission does not match packet")
        claims=v["claims"]
        if not isinstance(claims,list) or not 1<=len(claims)<=6:
            raise ValueError("expected one to six claims")
        evidence={e["id"] for e in packet["untrusted_data"]["evidence"]}
        for c in claims:
            if (not isinstance(c,dict) or set(c)!={"statement","evidence_ids","kind"}
                or c["kind"] not in {"observation","inference","unknown","contradiction"}
                or not isinstance(c["statement"],str) or not c["statement"].strip() or len(c["statement"])>700
                or not isinstance(c["evidence_ids"],list) or len(c["evidence_ids"])>6
                or any(not isinstance(i,str) or i not in evidence for i in c["evidence_ids"])
                or (c["kind"]!="unknown" and not c["evidence_ids"])):
                raise ValueError("invalid claim or unregistered evidence")
        questions=v.get("questions",[])
        if not isinstance(questions,list) or len(questions)>4 or any(not isinstance(q,str) or len(q)>300 for q in questions):
            raise ValueError("invalid evidence requests")
        if v["phase"]=="revision" and v.get("revision") not in {"retain","revise","retract"}:
            raise ValueError("a revision must explicitly retain, revise or retract")
        if v["phase"]=="decision" and v.get("decision") not in DECISIONS:
            raise ValueError("invalid research decision")
        if v.get("host_run_id") is not None and (not isinstance(v["host_run_id"],str)
                                                  or len(v["host_run_id"])>120):
            raise ValueError("invalid host run identifier")
        if "usage" in v and (not isinstance(v["usage"],dict) or set(v["usage"])-{"input_tokens","output_tokens"}
            or any(type(x) is not int or x<0 for x in v["usage"].values())):
            raise ValueError("invalid usage metrics")
        _,w=self.load()
        w["submissions"].setdefault(v["phase"],{})[role]=v
        write_json(self.track,w)

    def add_followup(self,path):
        s,w=self.load()
        if self.current(s,w)!="revision" or w["submissions"].get("revision") or w["followup"]:
            raise ValueError("one follow-up batch allowed before either revision")
        notes=evidence_file(path,ts(s["as_of"]))
        if not 1<=len(notes)<=12:
            raise ValueError("follow-up must contain 1–12 timestamped records")
        w["followup"]=[r|{"id":"E-"+digest(r)[:16]} for r in dedupe(notes)
                       if "E-"+digest(r)[:16] not in {e["id"] for e in s["evidence"]}]
        if not w["followup"]:
            raise ValueError("no new evidence in proposed batch")
        write_json(self.track,w)

    def report(self,paper=None,alerts=None):
        s,w=self.load()
        submissions=w["submissions"]
        decision=submissions.get("decision",{}).get("research-director",{}).get("decision")
        p=s["provenance"]
        if not p or not p["fresh"] or p["synthetic"] or s["technical"][p["frame"]]["bars"]<21:
            conclusion="insufficient evidence"
        else:
            conclusion=decision or "insufficient evidence"
        events=[r for r in s["evidence"]+w["followup"]
                if r["units"]=="event" and ts(r["observed"])>=ts(s["as_of"])]
        report=s|{"schema_version":1,"research_execution":w["method"],"pending_phase":self.current(s,w),
                  "submitted_host_outputs":submissions,"followup":w["followup"],"research_conclusion":conclusion,
                  "director_submitted_view":decision,"upcoming_events":events,"alerts":alerts or [],
                  "paper_account":paper,"execution_decision":"no simulated trade authorized by this report",
                  "limitations":["Host submissions are recorded as supplied. The CLI cannot authenticate who wrote them.",
                                 "Macro series are latest-vintage snapshots, excluded from historical signals.",
                                 "Simulated fills do not establish executable prices or future performance."]}
        write_json(self.root/"report.json",report)
        write(self.root/"report.md",markdown(report))
        return report

def markdown(r):
    def esc(v):
        return re.sub(r"([\\<>&\x60*_\[\]|])",r"\\\1",str(v).replace("\n"," ").replace("\r"," "))
    lines=["# XAUUSD research report", "", f"As of **{r['as_of']}** • Mode: **{r['mode']}**",
           f"Execution: **{r['research_execution']}**",f"**Conclusion: {r['research_conclusion']}**",
           r["execution_decision"],"", "## Market and data freshness",""]
    if p:=r["provenance"]:
        lines.append(f"- {esc(p['instrument'])}; {esc(p['delay'])}; age {p['age_seconds']} seconds; {r['gaps']} discontinuities.")
        if p["synthetic"]:
            lines.append("- **SYNTHETIC fixture. No real market observations.**")
    else:
        lines.append("- No accepted spot data.")
    lines+=["","## Technical findings",""]
    for f,s in r["technical"].items():
        if f!="session_levels" and s.get("bars"):
            lines.append(f"- {esc(f)}: {s['bars']} bars, close {s['last']:.3f}, {esc(s['regime'])}, RSI {s['rsi14']}, ATR {s['atr14']}, breakout {s['breakout']}.")
    lines+=["","## Macro, institutional and news evidence",""]
    for e in r["evidence"]+r["followup"]:
        if e["series"]!="SPOT_OHLC":
            lines.append(f"- {esc(e['id'])} {esc(e['instrument'])}: {esc(e['value'])} {esc(e['units'])} ({esc(e['observed'])}; fresh={e['fresh']}).")
            if "previous_observation" in e:
                prior=e["previous_observation"]
                lines.append(f"  - Change from {esc(prior['date'])}: {prior['change_native_units']:.4g} in series units.")
            if "year_over_year_percent" in e:
                lines.append(f"  - Year-over-year change: {e['year_over_year_percent']:.2f}%.")
    for k,v in r["price_yield_dollar_correlation"].items():
        lines.append(f"- Same-date change correlation for {k}: {v['r']} ({v['n']} pairs; descriptive only).")
    lines+=["","## Upcoming events and alerts",""]
    lines += [f"- {esc(e['observed'])}: {esc(e['instrument'])}" for e in r["upcoming_events"]] or ["- No dated events were verified in this run; absence is not evidence of an empty calendar."]
    lines += ["- "+esc(x) for x in r["alerts"]]
    labels={"independent":"Independent findings and bullish/bearish theses","cross":"Cross-examination and disagreements",
            "critique":"Independent critic","revision":"Thesis revisions","decision":"Director decision"}
    for p in PHASES:
        lines+=["", "## "+labels[p],""]
        for role,response in r["submitted_host_outputs"].get(p,{}).items():
            lines.append(f"- **{role}**"+(f" ({response['revision']})" if p=="revision" else ""))
            lines.extend(f"  - {esc(c['kind'])}: {esc(c['statement'])} [{', '.join(c['evidence_ids'])}]" for c in response["claims"])
            lines.extend("  - Evidence request: "+esc(q) for q in response.get("questions",[]))
        if not r["submitted_host_outputs"].get(p):
            lines.append("- No host submissions recorded.")
    lines+=["","## Historical simulation and independent risk","",
            "- Simulation status: "+esc(r["simulation"]["status"])+".",
            "- "+esc(r["risk_floor"]["note"])]
    for f in r["simulation"].get("test_folds",[]):
        m=f["out_of_sample"]
        lines.append(f"- Forward fold ending {m['last_bar_closed_at']}: {m['trades']} trades, virtual net closed P&L {m['pnl']:.2f}, max drawdown {m['max_drawdown']:.2%}; hold {m['buy_and_hold_pnl']:.2f}.")
    if r["paper_account"] and r["paper_account"].get("account"):
        a=r["paper_account"]
        lines.append(f"- Persistent virtual account: realized {a['realized_pnl']:.2f}, unrealized {a['unrealized_pnl_net_of_modeled_exit']:.2f}.")
    lines+=["","## Sources and limitations",""]
    for e in r["evidence"]+r["followup"]:
        lines.append(f"- {e['id']}: {esc(e['source'])} (retrieved {esc(e['retrieved_at'])})")
    lines+=["- "+esc(x) for x in r["gaps_and_errors"]+r["limitations"]]
    return "\n".join(lines)
