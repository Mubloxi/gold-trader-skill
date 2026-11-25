---
name: xauusd-research
description: Run evidence-based XAUUSD spot and MT5 gold research, bounded agent debate and virtual-only paper simulations.
---

# XAUUSD research desk

Run from the project containing gold_desk/. Use python -m gold_desk (on Windows, py -3 -m gold_desk).
Read docs/WORKFLOW.md for the evidence and response schema. Ask for the exact instrument if unclear.
Python is optional. If unavailable or the user wants chat-only mode, use supplied screenshots,
structured data, timestamped sources, or verified web research from the host when available.
Use the gold-scanner, gold-news, gold-risk and related skills for focused requests. Do not claim a
Python indicator, replay, paper fill or native role ran unless it did. For a chat-only review, give
a clearly labeled bull case, bear case and risk verdict based on the known evidence, and stop here.
The optional runtime instructions below apply only if Python is available and the user wants it.

For setup, list presets with broker list. Use broker paths PRESET to show local installed terminal paths.
When the user asks to set up their broker, run broker setup PRESET with the exact Market Watch symbol
if known and --terminal if they supplied or selected a path. Use a found path only if the preset matches
one install; ask for the exact executable if the result is ambiguous or missing. Never request a login,
password, API key value or account number. Show the saved profile and explain that MT5 handles sign-in.
Use broker use PROFILE when asked to change the default. Keep the broker config local; no secrets are saved.
For a quick scan, run market --require-fresh with the default profile or --broker PROFILE. Summarize the
real bid/ask, closed candle, wicks, RSI, MACD, EMA, and any stale or missing data. Avoid spawning agents
unless the user asks for a review. For a review, use prepare with the selected profile and the steps below.
Keep MT5 broker instruments separate from spot. The spot simulator does not use MT5 broker candles.
Alternatively use a fresh spot CSV, or Twelve Data with TWELVE_DATA_API_KEY configured in the shell.
If no feed is configured, name the missing prerequisite. Never silently switch to a demo. An offline synthetic
fixture is for demonstration only. No real orders, credential handling, unsolicited simulated entries or personalized buy/sell calls.

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
