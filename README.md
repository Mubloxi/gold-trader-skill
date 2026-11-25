# Gold Trader Skill — XAUUSD Research Desk

Research gold spot (XAUUSD) with Claude Code or OpenAI Codex. The project combines Python calculations, structured research roles, evidence records, historical simulations, and a **virtual-only** paper account.

> **Current status:** research and simulation software. It cannot place real trades or guarantee profits. Live data-provider calls and full standalone Claude Code and Codex execution have not been verified in the original build environment. See [validation results](docs/VALIDATION.md).

## What it does

- Analyzes completed gold candles across timeframes using moving averages, RSI, MACD, ATR, support, resistance, structure, and session windows.
- Collects source-attributed evidence. Optional providers cover spot prices, macro observations, Federal Reserve news, BLS dates, and CFTC positioning. Some feeds require an API key; live access depends on provider availability.
- Uses staged bull, bear, critic, and director research. Native host subagents are used when available; a sequential fallback is disclosed when they are not.
- Simulates trades with a configurable virtual balance, modeled costs, independent risk checks, a persistent journal, and historical walk-forward tests.
- Produces JSON and Markdown reports. No broker, exchange order, or real-money execution is included.

Gold spot, gold futures, CFDs, and ETFs are different instruments. This engine expects **spot XAUUSD candles**; don't label futures or CFD data as spot.

## Quick start on Windows

Install **Python 3.11 or later**, with the Python launcher, and extract the release ZIP into Downloads. Open PowerShell:

```powershell
cd "$env:USERPROFILE\Downloads\xauusd-research-desk"
py -3 --version
py -3 scripts/demo.py --out demo-run
```

The ZIP contains a top-level `xauusd-research-desk` folder. If your extraction tool added another folder, adjust the path to the one containing `scripts` and `README.md`.

**What success looks like:** the command prints JSON, exits without an error, and creates `demo-run\research\report.md`, `report.json`, and a virtual account database. Open the report:

```powershell
notepad .\demo-run\research\report.md
```

The demo's prices, trades, and results are **synthetic**. Run it again with a different output folder, for example `--out demo-run-2`, because it refuses to overwrite a populated demo folder. On Windows, if the timezone database is missing, install it with `py -3 -m pip install tzdata`.

### Run the tests

```powershell
py -3 -m unittest discover -s tests -v
```

You should see individual test results followed by `OK`. Tests validate calculations and software behavior; passing them does not establish profitability or live-provider access. See [the recorded test results](docs/VALIDATION.md).

## Install and use with Claude Code

From the extracted project folder, install to a new project folder:

```powershell
py -3 scripts/install.py claude --target "$env:USERPROFILE\Downloads\gold-lab-claude"
cd "$env:USERPROFILE\Downloads\gold-lab-claude"
claude
```

Inside Claude Code, enter:

```text
/xauusd-research
```

Example request: “Use the included synthetic fixture to prepare a quick XAUUSD research report. Explain each limitation and don't queue a paper trade.”

The installed skill is project-scoped. Start Claude in the installed project folder. Native subagent availability depends on the host and permissions. Claude Code, its account, and applicable usage charges are separate from this repository.

## Install and use with Codex

From the extracted project folder:

```powershell
py -3 scripts/install.py codex --target "$env:USERPROFILE\Downloads\gold-lab-codex"
cd "$env:USERPROFILE\Downloads\gold-lab-codex"
codex
```

Ask Codex:

```text
Use $xauusd-research to review a gold data file, explain the evidence and generate a research report.
```

`$xauusd-research` is the Codex skill mention, **not a slash command**. If your host supports subagents and permits them, the workflow can dispatch independent roles. Otherwise it identifies the sequential fallback.

## Commands and roles

| Where | Command | Purpose |
| --- | --- | --- |
| Claude Code | `/xauusd-research` | Start the project skill. |
| Codex | `$xauusd-research` | Mention the skill in a request. |
| Terminal | `py -3 -m gold_desk prepare --help` | Show evidence and report preparation options. |
| Terminal | `py -3 -m gold_desk status --help` | Check which research stage and roles are pending. |
| Terminal | `py -3 -m gold_desk packet --help` | Create an individual role's packet. |
| Terminal | `py -3 -m gold_desk submit --help` | Record a real host agent's response. |
| Terminal | `py -3 -m gold_desk followup --help` | Add a bounded batch of sourced evidence. |
| Terminal | `py -3 -m gold_desk report --help` | Write or refresh the report. |
| Terminal | `py -3 -m gold_desk alerts --help` | Poll configured price and event alerts. |
| Terminal | `py -3 -m gold_desk paper-step --help` | Queue or advance a virtual hypothesis. |
| Terminal | `py -3 -m gold_desk account --help` | Show the virtual account and journal. |

**There are no separate `/bull` or `/sell` slash commands.** The skill coordinates role profiles, including scanner, news, entry, exit, time machine, risk, budget, paper broker, alerts, macro, institutional, bull, bear, critic, and director. Their named definitions are under the relevant platform's agents folder; actual dispatch depends on host capabilities. See [WORKFLOW.md](docs/WORKFLOW.md).

## Push the project to your GitHub repository

The repository already exists at [Mubloxi/gold-trader-skill](https://github.com/Mubloxi/gold-trader-skill). Install Git for Windows and sign in through Git Credential Manager if prompted. Extract the ZIP in Downloads first, then run:

```powershell
cd "$env:USERPROFILE\Downloads"
git clone https://github.com/Mubloxi/gold-trader-skill.git
robocopy ".\xauusd-research-desk" ".\gold-trader-skill" /E /XD .git __pycache__ .gold-cache demo-run research-run /XF .env *.sqlite *.pyc
cd .\gold-trader-skill
git status
git add -A
git commit -m "Add XAUUSD gold research skill"
git push origin main
```

Only run `git add -A` after checking `git status`; don't copy API keys, local account databases, or unrelated files. If the destination folder already exists, inspect it instead of cloning over it. Git may ask you to configure your name and email for the commit.

---

# Detailed reference

A local gold spot research skill for Claude Code and Codex. The engine calculates indicators in Python, keeps timestamped evidence, runs chronological simulations, and manages an independent virtual ledger. Host agents can debate competing theses using staged evidence packets. No brokerage connectors, external execution, or guaranteed signals.

## Reproduce the demo

Use Python 3.11 or newer. Linux/macOS typically provide the IANA timezone database. On Windows, install timezone data if absent: `py -3 -m pip install tzdata`. No provider account or model call is required for the demo.

```sh
python scripts/demo.py --out demo-run
python -m unittest discover -s tests -v
```

The demo starts with $250 in virtual cash, queues a hypothetical setup, advances it on subsequent synthetic candles, and writes the SQLite journal and JSON/Markdown reports. Amounts and trades are software examples, not market results.

## Install in a project

From the extracted repository, install into a new or empty directory, then launch your host from that directory.

| Host | Linux/macOS | Windows PowerShell | Discovery |
| --- | --- | --- | --- |
| Claude Code | `./install.sh claude --target ./gold-lab` | `.\install.ps1 -Platform claude -Target .\gold-lab` | `.claude/skills`, `.claude/agents`; invoke `/xauusd-research` |
| Codex CLI | `./install.sh codex --target ./gold-lab` | `.\install.ps1 -Platform codex -Target .\gold-lab` | `.agents/skills`, `.codex/agents`; invoke `$xauusd-research` |
| Standalone Python | Run from unpacked repository | Use `py -3` instead of `python` | Deterministic reports; no agents |
| Claude plugin loader | From the extracted root, use `claude --plugin-dir .` | Same, from the extracted root | Plugin variant of same Claude definitions; run Python from the extracted root |

Project files are copied without dependencies, secrets, or overwrites of differing files. On Windows you can also run `py -3 scripts/install.py codex --target gold-lab` if local PowerShell policy blocks scripts. If the host cannot start agents, follow the explicitly labeled sequential fallback. Host plan limits and sandbox permissions still apply. Claude's skill and subagent formats and Codex's directories and TOML were checked against [Claude skills](https://code.claude.com/docs/en/skills), [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Codex skills](https://developers.openai.com/codex/skills), and [Codex subagents](https://developers.openai.com/codex/subagents).

## Research your instrument

1. Export legally usable indicative spot candles from a data provider. Put the candle close time in UTC in column `close_time`, followed by `open,high,low,close`. Rows must be ascending, unique and aligned to the frame. Do not pass GC futures, a CFD export or GLD as spot.
2. Put beside `spot.csv` a `spot.json` document using the shape in [config/spot.example.json](config/spot.example.json). Record actual source, retrieval time and quote basis. Supported frames: 1m, 5m, 15m, 30m, 1h and 4h. Spot has no central volume field; none is assumed.
3. Run:

```sh
python -m gold_desk prepare --csv spot.csv --public --mode standard --session research-run/001
python -m gold_desk report --session research-run/001
```

Use `--method native-host` only when the platform will dispatch real subagents, as described in [the agent workflow](docs/WORKFLOW.md). Use `--evidence notes.json` for verified observations or upcoming events. See [the source catalog](docs/SOURCES.md) and the [evidence example](config/evidence.example.json). The example shows formatting only; correct its dates and verify the values before import. Use `--holidays config/holidays.example.json` only as a format example: replace with holidays and shortened trading hours verified for your source (date and integer close hour are New York time).

Optional: `--twelve 5m` makes Twelve Data primary and the supplied CSV fallback. Set `TWELVE_DATA_API_KEY` in your shell; the program does not automatically load .env files. The server may require a plan with gold data, and latency varies. Cached or delayed data always retains its recorded timestamp and latency label. Daily macro observations are context, not short-term trade timing.

## Paper simulator

```sh
python -m gold_desk paper-step --csv spot.csv --db virtual.sqlite --config config/paper.example.json --queue
python -m gold_desk paper-step --csv spot.csv --db virtual.sqlite --config config/paper.example.json
python -m gold_desk account --db virtual.sqlite
```

The first command can queue a deterministic hypothetical breakout on the latest completed bar; it may decline if the feed is stale or there is no setup. Use the second command as updated overlapping candle exports arrive. Replaying old candles never duplicates events. A ledger is pinned to its provider identity, frame, quote type, synthetic flag and risk settings; start a new database to change them. Virtual shorts are symmetric fully collateralized simulations with no borrowing facility or carry model. Gaps may exceed a planned loss, even with hard risk caps on new positions.

Alerts are polling only: `python -m gold_desk alerts --session research-run/001 --above 4000 --hours 24`. Prepare a fresh snapshot per poll; alert state suppresses repeats. Thresholds refer to completed candles and scheduled event notes, not orders. The program does not start a scheduler.

## Troubleshooting

- **Stale or missing bars**: verify symbol, feed, frame, close time and entitlement. The desk fails closed. It never fabricates a current price or substitutes futures.
- **Insufficient coverage**: use the provider warnings and source catalog; add only verified source records. Longer frames and replay need enough history.
- **Timezone lookups fail**: install IANA tzdata via the OS, or the Python tzdata package in the same runtime.
- **Agent not discovered**: restart from the installation target; check the project trust settings and host subagent support. Do not claim native execution when the host cannot dispatch it.
- **Position history missing**: provide an updated export containing the last processed candle and subsequent observations. Avoid changing the pinned source.
- **Config incompatibility**: compare your JSON against the supplied examples; choose a new session/database when changing provenance or risk rules.

See [architecture](docs/ARCHITECTURE.md), [upstream audit and plan](docs/IMPLEMENTATION-PLAN.md), [validation results](docs/VALIDATION.md), and [attribution](NOTICE).
