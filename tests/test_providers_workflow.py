import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError

from gold_desk.core import ts, iso, write_json, read_json
from gold_desk.providers import Client, ProviderError, parse_twelve, fred, cot, treasury, dedupe, bls_events, fed_news, evidence_file, TWELVE
from gold_desk.workflow import Review, snapshot
from gold_desk.paper import Rules
from gold_desk.cli import alerts
from gold_desk.core import csv_feed

T=ts("2025-01-09T19:40:00Z")
HERE=Path(__file__).parent

class Providers(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
    def client(self,transport):
        return Client(self.path,transport,clock=lambda:T,pause=lambda n:None)

    def test_retries_caches_and_excludes_auth_from_cache(self):
        calls=[]
        def wire(url,h):
            calls.append((url,h))
            if len(calls)<2:
                raise HTTPError(url,429,"Mock",{"Retry-After":"0"},None)
            return "accepted"
        c=self.client(wire)
        self.assertEqual(c.get(TWELVE,authorization="apikey MOCK_KEY")[0],"accepted")
        self.assertEqual(c.get(TWELVE,authorization="apikey MOCK_KEY")[0],"accepted")
        self.assertEqual(len(calls),2)
        self.assertNotIn("MOCK_KEY",calls[-1][0])
        self.assertNotIn("MOCK_KEY",next(self.path.glob("*.json")).read_text())
        with self.assertRaises(ProviderError): c.get("https://example.org/")
    def test_rate_limit_and_bad_schema_not_cached(self):
        def wire(url,h): raise HTTPError(url,429,"mock",{"Retry-After":"99"},None)
        with self.assertRaisesRegex(ProviderError,"rate limited"): self.client(wire).get(TWELVE)
        with self.assertRaisesRegex(ProviderError,"invalid response"):
            self.client(lambda u,h:"bad").get(TWELVE,parser=lambda b,t:json.loads(b))
        self.assertFalse(list(self.path.glob("*.json")))
    def test_twelve_open_time_and_closing_filter(self):
        data={"meta":{"symbol":"XAU/USD","interval":"5min"},"values":[
          {"datetime":"2025-01-09 19:35:00","open":"2000","high":2004,"low":1999,"close":2002},
          {"datetime":"2025-01-09 19:40:00","open":"2002","high":2005,"low":2001,"close":2003}]}
        f=parse_twelve(json.dumps(data),T,"5m")
        self.assertEqual(f.closed(T)[0].close_time,T)
        self.assertEqual(len(f.closed(T)),1)
        data["meta"]["symbol"]="GC"
        with self.assertRaises(ProviderError): parse_twelve(json.dumps(data),T,"5m")
    def test_fred_missing_markers_dates_and_treasury_fallback_parser(self):
        a,v=fred(self.client(lambda u,h:"observation_date,DFII10\n2025-01-07,2.0\n2025-01-08,.\n2025-01-10,3\n"),"DFII10",T)
        self.assertEqual(v,{"2025-01-07":2.})
        self.assertIsNone(a["available_at"])
        xml='<feed xmlns="urn:atom" xmlns:m="urn:meta" xmlns:d="urn:data"><entry><content><m:properties><d:NEW_DATE>2025-01-07T00:00:00</d:NEW_DATE><d:TC_10YEAR>1.79</d:TC_10YEAR></m:properties></content></entry></feed>'
        self.assertEqual(treasury(self.client(lambda u,h:xml),"DFII10",T)[0]["value"],1.79)
    def test_cftc_net_is_contracts_and_observation_not_release(self):
        data=[{"report_date_as_yyyy_mm_dd":"2025-01-07T00:00:00","cftc_contract_market_code":"088691",
              "m_money_positions_long_all":"900","m_money_positions_short_all":"600","open_interest_all":"2600"}]
        r=cot(self.client(lambda u,h:json.dumps(data)),T)[0]
        self.assertEqual(r["value"]["net"],300)
        self.assertIsNone(r["available_at"])
        self.assertEqual(r["units"],"contracts")
    def test_calendar_handles_tz_and_rss_deduplicates(self):
        body="BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;TZID=America/New_York:20250110T083000\nSUMMARY: Employment Situation\nEND:VEVENT\nEND:VCALENDAR"
        e=bls_events(body,T,T)[0]
        self.assertEqual(e["observed"],"2025-01-10T13:30:00Z")
        rss="<rss><channel><item><pubDate>Wed, 08 Jan 2025 16:00:00 GMT</pubDate><title>Policy update</title><link>https://www.federalreserve.gov/a</link></item></channel></rss>"
        items=fed_news(rss,T,T)
        self.assertEqual(len(dedupe(items+items)),1)
        with self.assertRaises(ProviderError): fed_news("<!DOCTYPE rss>"+rss,T,T)
    def test_manual_evidence_rejects_future_publication(self):
        path=self.path/"evidence.json"
        write_json(path,[dict(series="FOMC",instrument="Fixture",value="scheduled",units="event",
                        source="https://www.federalreserve.gov/",observed="2025-01-10T14:00:00Z",
                        available_at="2025-01-10T12:00:00Z",retrieved_at=iso(T))])
        with self.assertRaisesRegex(ValueError,"unavailable"): evidence_file(path,T)

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)
        self.file=self.dir/"submission.json"
        self.review=Review(self.dir/"session")
        f=csv_feed(HERE/"fixtures/synthetic-gold.csv",T)
        self.snap=snapshot(f,T,"quick",Rules(),[],[],10,{})
    def send(self,role,**others):
        p=self.review.packet(role)
        response={k:p[k] for k in ("phase","snapshot_digest","role")}
        response.update(claims=[{"statement":"SYNTHETIC test submission; do not present as an agent action",
                      "kind":"unknown","evidence_ids":[]}])
        response.update(others)
        write_json(self.file,response)
        self.review.submit(role,self.file)
    def test_stages_isolate_then_record_retraction_and_dissent(self):
        self.review.start(self.snap,"sequential-role-fallback")
        self.send("bull-researcher")
        self.assertEqual(self.review.packet("bear-researcher")["previous_phase_submissions"],{})
        self.send("bear-researcher")
        self.send("risk-manager")
        self.assertIn("bull-researcher",self.review.packet("bear-researcher")["previous_phase_submissions"]["independent"])
        self.send("bull-researcher")
        self.send("bear-researcher")
        self.send("independent-critic",questions=["Do we have a verified Fed date?"])
        note=self.dir/"evidence.json"
        write_json(note,[dict(series="FOMC",instrument="SYNTHETIC calendar fixture",value="scheduled",units="event",
                   source="https://www.federalreserve.gov/",observed="2025-01-10T14:00:00Z",
                   available_at=iso(T),retrieved_at=iso(T))])
        self.review.add_followup(note)
        self.assertEqual(len(self.review.packet("bear-researcher")["untrusted_data"]["evidence"]),2)
        self.send("bull-researcher",revision="retract")
        self.send("bear-researcher",revision="retain")
        self.send("research-director",decision="bearish")
        r=self.review.report()
        self.assertEqual(r["research_conclusion"],"insufficient evidence")
        self.assertEqual(r["director_submitted_view"],"bearish")
        self.assertEqual(r["submitted_host_outputs"]["revision"]["bull-researcher"]["revision"],"retract")
    def test_unregistered_claim_and_snapshot_tamper_are_rejected(self):
        self.review.start(self.snap,"native-host")
        with self.assertRaisesRegex(ValueError,"unregistered"):
            self.send("bull-researcher",claims=[{"statement":"Fixture","kind":"observation","evidence_ids":["forged"]}])
        write_json(self.review.base,self.snap|{"instrument":"not allowed"})
        with self.assertRaisesRegex(ValueError,"integrity"): self.review.load()
    def test_offline_missing_produces_report_without_fake_agents(self):
        self.review.start(snapshot(None,T,"quick",Rules(),[],["data missing"],10,{}),"offline-no-agents")
        r=self.review.report()
        self.assertEqual(r["submitted_host_outputs"],{})
        self.assertIsNone(r["pending_phase"])
        self.assertEqual(r["research_conclusion"],"insufficient evidence")
    def test_alerts_dedupe_and_reset(self):
        self.review.start(self.snap,"offline-no-agents")
        state=self.dir/"alerts.json"
        self.assertEqual(len(alerts(self.review,state,2000,None,24)),1)
        self.assertFalse(alerts(self.review,state,2000,None,24))
        self.assertFalse(alerts(self.review,state,4000,None,24))
        self.assertEqual(len(alerts(self.review,state,2000,None,24)),1)
