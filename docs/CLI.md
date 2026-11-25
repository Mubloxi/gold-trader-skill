# Optional Python CLI

## Windows + Pepperstone or another MT5 broker

**New:** See the [broker setup and prompt guide](QUICK-START.md) to save Pepperstone, Vanga, or another MT5 terminal as a reusable profile. For a standard Pepperstone installation:

```powershell
py -3 -m gold_desk broker setup pepperstone --symbol XAUUSD
py -3 -m gold_desk market --require-fresh
```

If the first command finds zero or multiple installs, use `broker paths pepperstone` and pass the correct `--terminal` path. Sign into MT5 first and install its Python package as described below. The connection is checked by `market`, not by saving the profile.


1. Open **desktop MetaTrader 5** on the same Windows PC as Python. Sign in there, preferably using a demo account for setup. You do not give the skill a broker password, account number, or investor password.
2. In **Market Watch**, find your broker's gold symbol. Open its chart. If the terminal shows a suffix, such as `XAUUSD.a`, use the exact symbol shown. The adapter verifies that the broker identifies the symbol as non-expiring XAU/USD. It rejects unrelated instruments and expiring futures.
3. Run this from the extracted project or installed skill project:

```powershell
py -3 -m pip install MetaTrader5
py -3 -m gold_desk market --mt5 5m --mt5-symbol XAUUSD --require-fresh --out .\research-run\mt5-market.json
```

This command prints actual terminal data as JSON and writes a copy you can give to Claude Code or Codex. There is no AI call in this step. It uses the [official MetaTrader 5 Python interface](https://www.mql5.com/en/docs/python_metatrader5) and talks to your **local desktop terminal**, which already connects to Pepperstone or your chosen broker. The MT5 web terminal, mobile app, and a cloud agent do not provide that local connection. If you use an agent in the cloud, run the export on Windows and provide the JSON file to the agent. Live connectivity still needs to be checked on your PC.

If several MT5 installations are present, specify `--mt5-terminal "C:\path\to\terminal64.exe"`. This command supports `1m`, `5m`, `15m`, `30m` and `1h`. The default freshness limit is 10 minutes; for hourly bars you can intentionally choose a larger candle age with `--max-age 65`. During closed markets, the last candles or quote can be stale. Omit `--require-fresh` only if you deliberately want to inspect stale data with its age shown.

### What the AI reads

- **Quotes:** last available bid, ask, spread and UTC tick time, with quote age and a freshness flag. The last quote can be absent even when candle data is present.
- **Completed candles:** UTC close timestamp, open, high, low, close, body size, range, upper wick, lower wick and direction. MT5's current forming bar is skipped; the latest bar may remain unavailable until MT5 advances to the next bar.
- **Indicators:** RSI14, ATR14, MACD 12/26/9 with signal and histogram, EMA9/20/50/200, Wilder RMA14 of closes, and SMA10/20/50. Missing history produces null values. Indicators use returned completed candles; seed and warmup conventions can differ from indicators displayed on your chart.

MT5 candles are **broker instrument quotes**, often from a CFD, and the chart basis is identified as bid, last, or unknown. They are not interchangeable with an independent XAU/USD spot benchmark. The integration does not place orders or connect broker prices to the existing spot paper simulator.

### Prepare an AI research session using MT5

```powershell
py -3 -m gold_desk prepare --mt5 5m --mt5-symbol XAUUSD --mode quick --session .\research-run\mt5-review
notepad .\research-run\mt5-review\report.md
```

This writes a report with numeric evidence without spending model usage. To run host agents, install the appropriate package below, start Claude Code or Codex from that project, and explicitly ask it to use your MT5 symbol and build a report. Ask it to check price and quote timestamps first. Add `--public` only when you also want separate macro sources and accept their network requirements. Keep JSON from your broker private if its terms prohibit redistribution.

### Use Twelve Data without MT5

```powershell
$env:TWELVE_DATA_API_KEY = Read-Host "Twelve Data API key" -MaskInput
py -3 -m gold_desk market --twelve 5m --require-fresh
```

`-MaskInput` needs PowerShell 7. On Windows PowerShell 5.1, use `$env:TWELVE_DATA_API_KEY = "YOUR_KEY"` locally, or set the environment variable outside PowerShell. Never paste your real key into chat or commit it to Git. The key is only for Twelve Data; it is unrelated to your Claude or Codex account. A fresh timestamp does not guarantee exchange-grade real-time delivery.


## Research your instrument

1. Export legally usable indicative spot candles from a data provider. Put the candle close time in UTC in column `close_time`, followed by `open,high,low,close`. Rows must be ascending, unique and aligned to the frame. Do not pass GC futures, a CFD export or GLD as spot.
2. Put beside `spot.csv` a `spot.json` document using the shape in [config/spot.example.json](../config/spot.example.json). Record actual source, retrieval time and quote basis. Supported frames: 1m, 5m, 15m, 30m, 1h and 4h. Spot has no central volume field; none is assumed.
3. Run:

```sh
python -m gold_desk prepare --csv spot.csv --public --mode standard --session research-run/001
python -m gold_desk report --session research-run/001
```

Use `--method native-host` only when the platform will dispatch real subagents, as described in [the agent workflow](WORKFLOW.md). Use `--evidence notes.json` for verified observations or upcoming events. See [the source catalog](SOURCES.md) and the [evidence example](../config/evidence.example.json). The example shows formatting only; correct its dates and verify the values before import. Use `--holidays config/holidays.example.json` only as a format example: replace with holidays and shortened trading hours verified for your source (date and integer close hour are New York time).

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

See [architecture](ARCHITECTURE.md), [upstream audit and plan](IMPLEMENTATION-PLAN.md), [validation results](VALIDATION.md), and [attribution](../NOTICE).
