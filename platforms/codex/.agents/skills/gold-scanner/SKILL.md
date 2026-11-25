---
name: gold-scanner
description: Analyze real XAU/USD candles, chart structure and available gold indicators.
---

# gold-scanner

This skill works without Python. Use the host's available tools and user-supplied evidence.
For current market claims require an identifiable instrument, dated source and timestamp.
Label stale, delayed, synthetic and unavailable evidence clearly. Never default to a demo.
No broker execution or credentials. Use only public material or data the user supplied.
When unable to verify a value, say what is missing. Do not fabricate readings or fills.

Use timestamped XAU/USD OHLC, an exported MT5 market JSON file, or a readable chart supplied by the user. Prefer structured values. If Python and an existing broker profile are available locally, use the market command with --require-fresh as documented. Confirm instrument, price source, timeframe, time zone, and whether the candle is closed. Summarize trend, range, levels, and candle structure. Transcribe clearly legible chart values only; flag uncertainty. Don't invent indicators or extract exact prices from unlabelled pixels.
