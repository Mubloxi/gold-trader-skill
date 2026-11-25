# Implementation and validation summary

Validated on Linux with Python 3.12.14. See [TEST-LOG.txt](TEST-LOG.txt) for the actual test output.

| Surface | Observed result |
| --- | --- |
| Unit and integration suites | 33 passed. Covers indicators, bar alignment, timestamp causality, sessions and DST, gaps, conservative ambiguous stops, no-leverage exposure and risk veto, persistent ledger, replay ordering, bootstrap reproducibility, stale/missing inputs, provider parsers and retry/cache behavior, staged agent packet validation, alerts, installers and full offline virtual account demo. |
| Linux project installation | Both shell installation commands ran in fresh projects. Installed Python CLI ran against missing data in both projects and produced an honest insufficient-evidence report. TOML profile names and Claude manifest paths validated locally. |
| Windows and macOS | Shared Python installer and static PowerShell wrapper checks passed. PowerShell, macOS and Claude Code were not available for native execution here. Windows timezone support may need tzdata. |
| Codex CLI runtime | CLI 0.172.0-alpha.2 was present. Native smoke command stopped before any agent invocation because this environment could not open the client's state database on its read-only filesystem. CLI-native execution is unverified. |
| Real subagent workflow | The current Codex host's collaboration interface ran five distinct native roles, producing nine actual submissions across independent research, cross-examination, critique, revisions and director decision. Replies were transferred into the packet protocol and validated by the CLI. No external data or simulated fill was used in that run. This validates the handoff in this host, not automatic discovery of packaged CLI or Claude profiles. |
| Live feeds | FRED graph CSV and CFTC endpoint probes timed out from the build environment. No Twelve Data subscription key was used. Provider transforms are verified with controlled fixtures, not with a successful live payload from this environment. |
| Offline virtual demo | Generated five disjoint holdout folds and an SQLite journal with hypothesis, risk, open and close events. Synthetic final virtual balance was 250.5298 USD from 250.00 USD, including modeled costs. This only tests the program. |

## Reproduction

```sh
python -m unittest discover -s tests -v
python scripts/demo.py --out demo-run
./install.sh claude --target ./claude-install-check
./install.sh codex --target ./codex-install-check
```

- [Offline report](../examples/offline-demo/report.md): deterministic market simulation; no host agent replies.
- [Native host report](../examples/native-agent-demo/report.md): genuine debate on the frozen synthetic fixture. The director submitted no simulated trade; the reporting layer marks synthetic evidence insufficient for a market conclusion. No token usage was supplied by the host and none was invented.

## Remaining operational limits

The automatic adapters cover spot (optional entitlement), FRED macro observations, Treasury yield fallback, BLS calendar, Fed monetary headlines, and CFTC futures positioning. FOMC and BEA schedules, exact DXY and COMEX futures quotes, central-bank purchases, ETF flows, PMI, independent liquidity observations and geopolitical reporting require verified timestamped evidence input. There is no comprehensive news wire, venue holiday API, guaranteed free real-time XAUUSD feed or built-in scheduler. Latest-vintage macro data is kept out of replay. Agent independence and capability restrictions depend on the host. The default demo needs no subscription and cannot establish real market performance.
