# Gold Trader Skill

Eleven XAU/USD research skills for **Codex** and **Claude Code**. Analyze candles, search for gold news, review hypothetical setups, and check risk one step at a time.

**Python is optional.** The skills can work with a screenshot, data you paste, or sources your AI can browse. Python is required for direct MT5 data, deterministic indicators and replays, and the virtual ledger. There is no live order execution.

## Easy Windows setup

Extract the ZIP and double-click **START-HERE.cmd**. Choices 1–2 are Codex/Claude Code with MT5, 3–4 are screenshot-only, and 5–6 are desktop app handoff. For MT5, install Python and approve the MetaTrader5 package if prompted. Log in to a demo account within desktop MT5; setup verifies the terminal reports it as demo before exporting. No broker credentials or orders are handled by the script.

The clipboard receives a suggested prompt. CLI clients can run it in the project; for desktop apps, open the project folder if supported or attach `research-run/mt5-market.json`. Clipboard copying is not automatic prompt submission. Claude Desktop and ChatGPT desktop skill discovery varies by environment; attaching JSON and pasting the prompt is the reliable fallback.

MT5 checks append snapshots to `research-run/observations.jsonl`. They contain market prices and indicator calculations, not account credentials. Compare each timestamp, symbol, OHLC, bid/ask and indicators against your terminal; different candle bases, warmup and current vs closed bars can explain differences. The log does not measure prediction accuracy or create AI forecasts. For a meaningful evaluation, record a timestamped forecast and invalidation before an outcome, then compare all forecasts with later observed data and include losses and missing results. Do not upload account details or private logs.

Select or create a **demo account in MT5** before running the check. The tool uses the account already connected in the terminal; MT5 controls account creation and account switching. If you have only one account and it is already signed in, no selection is needed. The setup uses a read-only MT5 interface. It does not trade. It has not been tested on Windows PowerShell or a live broker in this environment.

## Other installation options

Extract the ZIP, open the extracted folder and double-click **START-HERE.cmd**. Choose Codex or Claude, then screenshot mode or MT5. Screenshot mode does not require Python. MT5 mode guides you through Python, broker selection and a real data check. This Windows setup has not been verified against a live broker.

## Install with no Python on Windows

Download `gold-trader-skill-v1.3.zip` to Downloads, then open PowerShell:

```powershell
cd "$env:USERPROFILE\Downloads"
Expand-Archive -LiteralPath .\gold-trader-skill-v1.3.zip -DestinationPath .\gold-skill-v13
cd .\gold-skill-v13\xauusd-research-desk
```

### Codex

Run from that folder. Keep the folder open as your project in Codex:

```powershell
Copy-Item .\platforms\codex\.agents -Destination . -Recurse -Force
```

Start or restart Codex in that folder (enter `codex` if you use the CLI). Start with:

> Use $gold-scanner to review this XAU/USD chart. Use only the values you can verify and tell me what’s missing.

Attach a chart, paste OHLC numbers, or provide a source with a timestamp. Use `$gold-risk` to review a hypothetical setup or `$xauusd-research` to combine scanning and review. Dollar-prefixed names are Codex skill mentions.

Optional: copy `platforms\codex\.codex` to the project root the same way if you also want the custom subagent definitions. They are not needed for the chat-only skills.

### Claude Code

Run from the extracted folder:

```powershell
Copy-Item .\platforms\claude\.claude -Destination . -Recurse -Force
claude
```

In Claude Code, enter `/gold-scanner`, then attach or paste your gold data. Use `/xauusd-research` for a combined review.

After the updated version is pushed to GitHub, Claude Code also has a marketplace install option:

```text
/plugin marketplace add Mubloxi/gold-trader-skill
/plugin install gold-trader-skill@gold-trader-skill
```

With the plugin, use the qualified command `/gold-trader-skill:gold-scanner`. The project-local copy above uses the shorter `/gold-scanner`. For the optional Python commands, work from a checkout or extracted folder containing `gold_desk`.

### Any chat

Paste a [skill's SKILL.md](platforms/claude/.claude/skills/gold-scanner/SKILL.md) plus your chart or data into the chat. This gives the AI the review instructions; it cannot connect to your desktop MT5. If a value isn't visible, timestamped, or supplied, it should say so.

## The eleven

| Claude Code | Codex | Job |
| --- | --- | --- |
| `/gold-scanner` | `$gold-scanner` | Candles, wicks, indicators and levels |
| `/gold-news` | `$gold-news` | Dated releases, events and sources |
| `/gold-entry` | `$gold-entry` | Hypothetical confirmation and invalidation |
| `/gold-exit` | `$gold-exit` | Review stop, target, gaps and exit assumptions |
| `/gold-replay` | `$gold-replay` | Read replay results or plan a reproducible replay |
| `/gold-risk` | `$gold-risk` | Check risk assumptions and missing evidence |
| `/gold-budget` | `$gold-budget` | Explain virtual sizing, costs and units |
| `/gold-paper` | `$gold-paper` | Explain a paper ticket or review the virtual ledger |
| `/gold-alerts` | `$gold-alerts` | Define conditions and review CLI alert output |
| `/gold-macro` | `$gold-macro` | Rates, real yields, dollar and releases |
| `/gold-positioning` | `$gold-positioning` | CFTC reports, ETF flows and central-bank evidence |

The original Day Trader handoff is still the idea: **scanner → news → hypothetical entry and exit → replay → budget and risk → paper review**. You can run one skill without the others. Chat-only mode does not create real replay results, exercise the virtual ledger, or run background alerts.

## Optional: actual broker candles from MT5

This does require **Python on the same Windows PC as desktop MT5**. You don't need an MT5 API key. Sign in directly inside the app, open the exact gold symbol in Market Watch, and run:

```powershell
py -3 -m pip install MetaTrader5
py -3 -m gold_desk broker setup pepperstone --symbol XAUUSD
py -3 -m gold_desk market --require-fresh --out .\research-run\market.json
```

The other presets are `vanga` and `generic`. If discovery finds zero or multiple installs, use `broker paths pepperstone` and enter the actual path with `--terminal "C:\path\to\terminal64.exe"`. Broker names and symbols depend on your installation. The adapter reads OHLC, wicks, bid/ask and calculates indicators without a model call; give the JSON to Codex or Claude for analysis. A cloud agent cannot attach directly to your desktop. A live Pepperstone or Vanga connection was not verified in the build environment.

Twelve Data is a separate spot provider: it requires `TWELVE_DATA_API_KEY` and a plan that covers the requested feed. Any offline demo in this repository uses synthetic data. Read [the broker setup guide](docs/QUICK-START.md), [the optional CLI reference](docs/CLI.md), or [validation notes](docs/VALIDATION.md).

## Updating the GitHub repo (maintainer)

Extract the ZIP as shown above. Copy from a fresh extraction so you don't publish local research runs or project settings. If you already ran the setup commands above, re-extract the ZIP to `gold-skill-v13-push` first:

```powershell
cd "$env:USERPROFILE\Downloads"
Expand-Archive -LiteralPath .\gold-trader-skill-v1.3.zip -DestinationPath .\gold-skill-v13-push
git -C .\gold-trader-skill-git remote get-url origin
git -C .\gold-trader-skill-git status --short
```

Only continue if the remote is `Mubloxi/gold-trader-skill` and you don't have local edits to preserve. Use your actual clone folder if named differently.

```powershell
git -C .\gold-trader-skill-git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "Git pull failed. Fix it before copying." }
robocopy .\gold-skill-v13-push\xauusd-research-desk .\gold-trader-skill-git /E /R:1 /W:1
if ($LASTEXITCODE -ge 8) { throw "File copy failed." }
cd .\gold-trader-skill-git
git status --short
```

Review the listed files before staging:

```powershell
git add -A
git commit -m "Add standalone gold research skills and Python-free setup"
git push origin main
```

If you don't already have a clone named `gold-trader-skill-git`, run `git clone https://github.com/Mubloxi/gold-trader-skill.git gold-trader-skill-git` from Downloads first. Don't clone into an existing folder.

[MIT license](LICENSE) · [Original Day Trader attribution](NOTICE)
