# Implementation plan and upstream audit

The input is Jake Schincariol's MIT-licensed Day Trader skill. Its Claude marketplace manifest exposes eleven independently callable skills. Each role reads short JSON payloads from the project, invokes standard-library Python, and writes state for later roles. Offline fixtures make the same command paths reproducible. Preserve this layering, explicit handoffs, independent checks, timestamped observations, local state and fixture-driven verification.

| Upstream script / skill / test family | Handoff and gold redesign |
| --- | --- |
| scanner / scan.py | Nasdaq symbol lists and Yahoo Spark fixtures feed watchlist.json; replace stock universe, opening range and calendar with one instrument, validated bars, continuous UTC buckets and session tags. Reuse Wilder RSI recurrence. |
| news / news.py | Yahoo RSS, price fixtures and SEC 8-K/CIK mapping fill news cache; retain deduplication and URL evidence, replace company filings with macro events and user-approved source evidence. |
| entry / entry.py | Completed equity bars and clock drive entry.json, with offline and network cases; preserve confirmed bars and replay clocks. |
| exit / exit.py | entry.json plus ATR and expiry produce plan.json; preserve True Range formula, fix execution model for gold cost units. |
| timemachine / timemachine.py | plan.json and compressed TSLA intraday history feed seeded simulations and historical replays; replace equity clock and move from same-slot scenarios to chronological holdouts and block bootstrap. |
| budget / size.py | plan.json, weights, prices and portfolio feed orders.json in broker shape; replace share lots, portfolio allocations and order fields with virtual troy ounces and modeled costs. |
| risk / check.py | Reads orders, config, latest prices, portfolio and broker decisions; records a fingerprinted verdict. Preserve a separate risk boundary and revalidate exact payload against actual simulated open and current ledger. |
| broker / ticket.py | Local approval log and portfolio; its SKILL.md and desktop example can invoke a brokerage connector. Remove connector and approval routing entirely. Replace with atomic local ledger and idempotent events. |
| alerts / alerts.py | Price, clock and time-trigger rules persisted in JSON; Yahoo/Stooq fixtures test polling and deduplication. Replace equity opening bell and use report snapshots, price levels and economic schedule. |
| analyst / facts.py | SEC XBRL metrics, company filings and fixtures; replace equity earnings with official macro series and event evidence. |
| pelosi / ptr.py | Congressional disclosure ZIP/PDF text and seen IDs; replace with CFTC managed money, ETF and central-bank evidence, separate observation and availability. |
| Plugin JSON, example configs, test loader and test_repo | Preserve platform-specific manifest, example settings and separate test suite with synthetic data. Replace brokerage configuration and stock fixtures. |

The audit inventoried every file: all eleven skill texts and Python tools, twelve role/repository test modules, the loader, both plugin JSON files and all example configs. Fixtures were grouped by schema and role, including compressed Yahoo chart histories and the House disclosure ZIP; the stock data is not redistributed.

1. Define provenance, close-time semantics, schema validation and provider boundaries.
2. Implement deterministic market statistics, paper risk and ledger; use one conservative fill kernel in forward and historical modes.
3. Add chronological validation, benchmark metrics and seeded uncertainty estimation.
4. Introduce an immutable, content-addressed evidence snapshot and bounded staged research protocol; expose native agents on both hosts.
5. Add platform installers, documentation, offline fixture, CLI integration tests and a packaged demonstration.

Input archive SHA-256: a417522153234847eeaab4f0b883de1843a3ebe9b1e3f4942581070c97562054.
