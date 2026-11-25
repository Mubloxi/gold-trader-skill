---
name: xauusd-research
description: Run evidence-based XAUUSD gold spot research, bounded agent debate and virtual-only paper simulations.
---

# XAUUSD research desk

Run from the project containing gold_desk/. Use python -m gold_desk (on Windows, py -3 -m gold_desk).
Read docs/WORKFLOW.md for the evidence and response schema. Ask for the exact instrument if unclear.
The engine analyzes indicative gold spot only; futures, CFDs, ETFs and DXY are separately labeled context.
Use a fresh, user-supplied OHLC export, or ask before trying an optional keyed provider. An offline synthetic
fixture is for demonstration only. No real orders, account connections, unsolicited simulated entries or personalized buy/sell calls.

1. Run prepare with a new --session directory, selected --mode (default standard) and the true --method.
   Use --public only for an explicitly requested current-data scan; do not scrape or trust arbitrary pages.
2. Run status. For each pending role, run packet SESSION_FLAG ROLE and save its stdout separately as JSON.
   In the independent round give each native agent only its own packet. Do not share the session location,
   other responses, earlier reasoning or strategy conclusions. Make each packet available read-only.
3. Collect the actual response and save it as JSON; submit one response at a time through the CLI. Never
   fabricate host runs, debate, telemetry or observations. If the host cannot start native agents, use a new
   session with sequential-role-fallback. In the fallback, use role-specific packets in order, avoid
   carrying information into the independent round, and disclose that true isolation is unavailable.
4. Repeat for cross-examination, critique, revision and decision (followup may be added once before
   revisions when new dated evidence answers a recorded question). Preserve dissent and retractions.
   Stop after the bounded stages. If data or host calls are unavailable, report actual gaps and pending roles.
5. Run report. Distinguish research conclusion from execution. paper-step is a separate explicit user action;
   require the user to request virtual execution. The Python risk gate always independently validates fills.
   Report sources, freshness, cost assumptions, unresolved uncertainty and the actual execution mode.

SESSION_FLAG is --session PATH, the exact same path for every operation.

Invoke explicitly with $xauusd-research. When allowed, spawn a separate native Codex subagent for each role using its xau-ROLE definition when exposed. Provide only the packet.
