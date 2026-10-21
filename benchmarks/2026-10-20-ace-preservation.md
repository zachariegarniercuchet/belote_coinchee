# Brooklyn ace-preservation fix — benchmark, 20 October 2026

After the shared partner-feeding correction, Brooklyn v2 wins more games on
this sample and makes about 78% of its contracts, but still declares only
about 32% of played deals. V1 takes about 50% and remains ahead in these
matchups. The before/after win-rate changes are uncertain: all corresponding
95% paired-seed intervals include zero.

## Frozen policy and protocol

- Source `1fea8bbab941a8b9500a6b735f50325353dc1a03`, including the shared Brooklyn
  ace-preservation fix. V1 and v2 were BOTH rerun; their old baselines were not
  reused. Their bidding policies and de Belote bots did not change.
- Brooklyn now feeds likely-lost points before an ace. Ace exceptions are A–10
  in hand, a late public cutting risk, or unavoidable legal cards. Merely
  having two cards left is not enough; a winning partner must appear safe.
- 400 complete games: 100 per matchup, target 1000, seeds 30000–30049, each
  played with Brooklyn on both teams. Dealer `seed % 4`, bot RNG
  `seed * 17 + seat`. Current web engine, normal bot search settings, display
  sleeps/broadcasts disabled. Runtime 4.5 minutes.
- All games completed. Seed swaps, game totals, win totals and declaring
  totals were validated. No silent exclusions, live-room changes or tuning.
- Approximate 95% percentile-bootstrap intervals resample whole seed pairs
  (4,000 resamples), not correlated games/deals as independent trials.
  Pointwise, exploratory intervals; no formal ranking-test p-values.
- Reused development seeds, not an independent holdout. Different play changes
  game lengths and later contracts; these are not fixed-contract card replays.

The running local server was NOT restarted. A read-only check of
`/api/bots` still returned the old Brooklyn v2 description, confirming stale
backend code. The server launches with `debug=False`: Python bot changes do
not hot-reload. Browser assets can refresh from disk, but bots need a server
restart; in-memory rooms/games are lost on restart. Render needs a push and
deployment; no push was performed.

## Results — capots included

Taking excludes cancelled deals only. Contract success is conditional on
declaring and uses the scoring engine's actual majority/success flag.
Every capot and its full score contributes to wins, target-score progression,
taking, contract success and the all-deal calibration view.

| Brooklyn | Opponent | Wins | Win interval | Taking | Contracts made | Mean bid |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| v1 | de Belote v2 | 55/100 | 47–63% | 304/600 (50.7%) | 245/304 (80.6%) | 102.40 |
| v2 | de Belote v2 | 31/100 | 23–39% | 193/600 (32.2%) | 152/193 (78.8%) | 98.55 |
| v1 | de Belote v3 | 47/100 | 40–53% | 310/615 (50.4%) | 243/310 (78.4%) | 102.65 |
| v2 | de Belote v3 | 22/100 | 15–30% | 201/613 (32.8%) | 157/201 (78.1%) | 98.86 |

The current v2-minus-v1 win differences are −24 percentage points against
de Belote v2 (95% paired-seed interval −35 to −13) and −25 against v3
(−34 to −16). V2's conditional contract success now approaches v1's, but its
declaring frequency remains much lower. The two versions still share the same
playing function; their auction choices differ.

## Before versus after the partner-feeding correction

Previous source: `865e23aa4a3ce80d6dde9b2f67aaaebbc2d92ef0`. Only the shared
Brooklyn playing policy changed between these snapshots; bidding was held
fixed. Paired comparisons preserve both seat-swap games for each seed.

| Brooklyn / opponent | Wins before → now | Difference (pp) | 95% paired interval (pp) | Contract success before → now |
| --- | ---: | ---: | --- | ---: |
| v1 / de Belote v2 | 53 → 55 | +2 | -4 to +8 | 78.4 → 80.6% |
| v2 / de Belote v2 | 24 → 31 | +7 | -1 to +15 | 72.2 → 78.8% |
| v1 / de Belote v3 | 50 → 47 | -3 | -10 to +4 | 77.3 → 78.4% |
| v2 / de Belote v3 | 19 → 22 | +3 | -4 to +10 | 74.9 → 78.1% |

All four before/after intervals include zero. V2's observed win gains should
not be presented as a demonstrated population-level improvement, nor v1's
mixed results as evidence of a stable gain or loss. No changes were made in
response to the results.

## Calibration — show both views

Margin = trick points + dix de der + belote − numeric bid; no awarded
contract/coinche bonus. Failed contracts stay in BOTH views. A capot gives a
special dix-de-der value, so its bonus raises the all-deal mean. It is excluded
only in the separately labelled ordinary-deal view, never from outcome rates.
The explicit Capot contract has no numeric bid to subtract; these bots do not
announce it, and every contract in this sample was numeric.

| Brooklyn / opponent | All N | Mean margin, INCLUDING capots | Capot deals | Ordinary N | Mean margin, NO capots | Ordinary median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 / de Belote v2 | 304 | +30.43 | 30 | 274 | +17.19 | +18 |
| v2 / de Belote v2 | 193 | +27.93 | 17 | 176 | +16.17 | +19 |
| v1 / de Belote v3 | 310 | +30.55 | 32 | 278 | +16.68 | +18 |
| v2 / de Belote v3 | 201 | +26.12 | 14 | 187 | +16.64 | +20 |

The capot-deal counts above refer to Brooklyn's own declared deals. All of
these capots were won by the declaring team in this sample (30, 17, 32 and 14
in table order). Other capots on opponents' contracts also remain in all
outcome rates and are retained in the side-specific JSON rows.

V2's ordinary mean cushion is about 16 points, versus about 17 for v1. Its
all-deal cushion is about 26–28, including capots. Neither figure by itself
establishes good bidding: v2 still yields the contract on roughly two-thirds
of played deals. Bid, opening-holding and trump-leading breakdowns are
retained in the JSON rather than omitted.

## Reproduce and inspect

See [README.md](README.md) and
[results-2026-10-20-ace-preservation.json](results-2026-10-20-ace-preservation.json).
The summary includes all eight bot-side rows, 400 game outcomes, and paired
before/after differences. Full optional output also retains per-game deal
records behind the summary.

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --pairs 50 --workers 4 --output results.json
```
