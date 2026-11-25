# Broker setup and first scan

Use a local Windows terminal and keep your broker signed in inside the desktop MT5 app. Install the MetaQuotes Python package through PowerShell: `py -3 -m pip install MetaTrader5`. Set no API key when using this path. Twelve Data is a separate optional provider and requires `TWELVE_DATA_API_KEY`.

## Pick a broker

Run these from the extracted project or a project where the skill was installed:

```powershell
py -3 -m gold_desk broker list
py -3 -m gold_desk broker paths pepperstone
py -3 -m gold_desk broker setup pepperstone --symbol XAUUSD
py -3 -m gold_desk market --require-fresh
```

Presets: `pepperstone`, `vanga` (user-configured MT5 install; unverified branding), and `generic` for any other MT5 broker. Use the exact gold name in Market Watch; `XAUUSD` is a starting default. Discovery checks immediate installation folders under Program Files and LocalAppData Programs. It lists candidates without launching them. It does not search every disk or guarantee an install will be found. If you use a custom folder, or `broker paths` returns more than one candidate, pass the real executable path:

```powershell
py -3 -m gold_desk broker setup generic --name my-broker --terminal "D:\Apps\My MT5\terminal64.exe" --symbol "XAUUSD.a"
py -3 -m gold_desk broker use my-broker
py -3 -m gold_desk broker show
py -3 -m gold_desk market --require-fresh --out .\research-run\market.json
```

Use the real values in place of the example path and symbol. To find the executable on Windows, open the broker's MT5 shortcut properties and check **Target**, or right-click the running MT5 process in Task Manager and choose **Open file location**.

The profile file is `%LOCALAPPDATA%\gold-trader-skill\brokers.json` on Windows. It records each profile's preset, exact executable path, symbol and timeframe, plus the active profile. There are no credentials. The CLI reads profiles only from this local file, outside the checkout. Saving selects the profile; it does not verify sign-in or quotes. `market` and `prepare` use the active profile with no feed flags; `--broker PROFILE` picks a different saved one for a single run. For a 15-minute candle with the preset, use `market --broker pepperstone --mt5 15m --max-age 20 --require-fresh`.

## Prompts to paste

Install the proper skill first from the extracted project (the target folder must be new or have matching files):

```powershell
py -3 scripts/install.py codex --target "$env:USERPROFILE\Downloads\gold-codex-v12"
py -3 scripts/install.py claude --target "$env:USERPROFILE\Downloads\gold-claude-v12"
```

Start your client in its installed target folder.

| Goal | Codex | Claude Code |
| --- | --- | --- |
| Set up | `Use $xauusd-research to set up Pepperstone. Find its terminal and ask me if there is more than one. Use XAUUSD.` | `/xauusd-research Set up Pepperstone using XAUUSD. Ask if there is more than one terminal.` |
| Scan with minimal usage | `Use $xauusd-research to summarize my latest closed MT5 gold candle. No subagents.` | `/xauusd-research Scan my active broker's gold candles. No subagents.` |
| Research review | `Use $xauusd-research for a quick bull, bear and risk review of fresh gold data from my active MT5 broker.` | `/xauusd-research Do a quick bull, bear and risk review using fresh MT5 data.` |

Codex uses a skill mention. Claude Code uses one slash command; the text after it says what to do. Setup and data export are local commands with no model calls. Asking Codex or Claude to run them uses host usage for that conversation. The research roles also use host usage. If the assistant is running in a cloud workspace without your Windows terminal, run the PowerShell scan locally and give the host the exported JSON to review.

The original [Day Trader skill](https://github.com/Jakeschincariol/day-trader-skill) uses a chain of specialist tasks and files. This desk keeps that design: scanner, news, entries/exits, replay, budget/risk, and paper execution or alerts as applicable. The stock earnings and disclosure roles become gold macro and positioning roles; a bull/bear/critic/director review adds traceable disagreements. See [implementation plan](IMPLEMENTATION-PLAN.md) for the mapping. Real broker order execution is not included.
