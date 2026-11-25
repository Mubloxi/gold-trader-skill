"""Gold-facing entry points inspired by the original specialist workflow."""

SCANNER = """Use timestamped XAU/USD OHLC, an exported MT5 market JSON file, or a readable chart supplied by the user. Prefer structured values. If Python and an existing broker profile are available locally, use the market command with --require-fresh as documented. Confirm instrument, price source, timeframe, time zone, and whether the candle is closed. Summarize trend, range, levels, and candle structure. Transcribe clearly legible chart values only; flag uncertainty. Don't invent indicators or extract exact prices from unlabelled pixels."""

SKILLS = {
    "gold-scanner": ("Analyze real XAU/USD candles, chart structure and available gold indicators.",
        SCANNER),
    "gold-news": ("Find and summarize sourced news and events relevant to gold.",
        "Use web search if available. Look for dated coverage and primary sources such as Fed releases, BLS and BEA. Separate release time from article time; distinguish known, expected and revised numbers. Cite links and label freshness. With no browsing, analyze supplied evidence only. Do not claim background monitoring."),
    "gold-entry": ("Review hypothetical gold entries and what would confirm or invalidate them.",
        "Use the supplied dated setup and current candle evidence. State what confirmation is actually present and what is still missing. Describe conditions and invalidation in a hypothetical or paper-only context. A screenshot of a forming candle alone cannot confirm a close."),
    "gold-exit": ("Review exits and invalidation for a supplied hypothetical gold trade.",
        "Read the stated entry, stop and target, source, and simulated costs. Explain target and stop assumptions and how gaps or unknown intrabar ordering affect replay. Do not modify orders or positions."),
    "gold-replay": ("Review historical gold replay results and distinguish simulations from market evidence.",
        "Use the included deterministic replay workflow only if Python and matching historical inputs are available. With no Python, explain an existing replay report or draft a concrete replay plan. Never invent win rates, P&L or backtest results."),
    "gold-risk": ("Review the assumptions and risk limits of a hypothetical gold setup.",
        "Check gaps, spread, data freshness, instrument, trade assumptions, and sizing inputs. Present pass, block or insufficient evidence with reasons. An AI review does not replace the Python simulator's independent risk veto. Do not authorize a live trade."),
    "gold-budget": ("Explain educational sizing and budgeting for a virtual gold account.",
        "Use the user's simulated balance, maximum hypothetical loss, stop distance, spread and broker contract units if supplied. Explain the formula and units, distinguish ounces from lots and point value, and leave unknowns blank. Do not infer margin terms or recommend live size."),
    "gold-paper": ("Review a simulated gold ticket, ledger or virtual execution workflow.",
        "Explain how a supplied paper ticket or ledger works. The bundled Python simulator accepts supported spot feeds only and its own risk gate controls fills. Without Python, outline a hypothetical ticket and mark it not recorded or executed. Never place broker orders or invent simulated fills."),
    "gold-alerts": ("Describe gold alert conditions or read a supplied alert report.",
        "State explicit thresholds or event conditions and note timestamp and source. Explain that the optional CLI polls only when run. A chat review does not start a scheduler or promise notifications."),
    "gold-macro": ("Analyze dated macro evidence affecting XAU/USD.",
        "Use sourced rates, real yields, dollar measures and inflation or labor data. Distinguish the broad dollar proxy from DXY. Separate observations from plausible mechanisms and report time mismatch. No repeatable correlation claim without matching, validated data."),
    "gold-positioning": ("Explain sourced CFTC, ETF flow and central-bank gold positioning evidence.",
        "Label report and observation dates separately. Distinguish COMEX futures positions, ETFs, central bank holdings and spot. Report publication lags and gaps. Cite supplied or retrieved evidence; do not treat lagged reports as current prices or orders."),
}

CHAT_RULES = """This skill works without Python. Use the host's available tools and user-supplied evidence.
For current market claims require an identifiable instrument, dated source and timestamp.
Label stale, delayed, synthetic and unavailable evidence clearly. Never default to a demo.
No broker execution or credentials. Use only public material or data the user supplied.
When unable to verify a value, say what is missing. Do not fabricate readings or fills.
"""
