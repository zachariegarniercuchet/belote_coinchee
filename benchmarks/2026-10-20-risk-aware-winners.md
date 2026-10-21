# Brooklyn risk-aware winning cards — benchmark, 20 October 2026

The new playing rule gives mixed, small changes on this sample. V1 remains
ahead of v2; v2 still declares only about one-third of played deals. No
before/after win difference clearly excludes zero.

## Frozen policy and protocol

- Source `7fc077f9d733cde168dbc84bbfbd9a9c88713018`. Both Brooklyn versions were rerun with
  their shared risk-aware winner selection: before last seat, cash the highest
  reasonably safe winner, otherwise play the weakest current winner; in last
  seat, cash the highest-point winner. Existing partner feeding and known-cut
  ducking remain. Safety uses public information, not hidden hands.
- Bidding and de Belote opponents unchanged. Previous snapshot:
  `1fea8bbab941a8b9500a6b735f50325353dc1a03`, after the ace-feeding correction
  but before this new winning-card rule.
- 400 complete games, 100 per matchup; target 1000. Seeds 30000–30049,
  each replayed with Brooklyn on team 0 and team 1. Dealer `seed % 4`;
  bot RNG `seed * 17 + seat`. Current web engine, normal bot settings,
  display sleeps/broadcasts disabled. Runtime 4.8 minutes.
- All 400 unique game keys and both seat swaps for all 50 seeds per matchup
  validated. Win totals, played-deal totals, declarations and successes
  reconciled with per-game records. No dropped games, outcome exclusions or
  tuning during/after the run.
- Approximate 95% percentile-bootstrap intervals use 4,000 resamples of whole
  seed pairs, preserving their dependent seat swaps and before/after matching.
  No normality assumption or hypothesis-test p-values. Intervals are pointwise
  and exploratory, not multiplicity-adjusted ranking tests.
- Reused development seeds, not a holdout. Changed card play changes game
  lengths and subsequent hands/contracts: these are full-game outcomes, not
  replays of identical fixed contracts.
- The running server was not restarted or modified, and nothing was pushed.

## Results — capots included

Taking excludes cancelled deals only. Success is the engine's actual
contract-reached flag, including its majority condition. Capots and their
full scores count in wins, taking, success and target-score progression.

| Brooklyn | Opponent | Wins | Win 95% interval | Taking | Contracts made | Mean bid |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| v1 | de Belote v2 | 55/100 | 49–61% | 305/605 (50.4%) | 240/305 (78.7%) | 102.46 |
| v1 | de Belote v3 | 48/100 | 40–55% | 306/614 (49.8%) | 240/306 (78.4%) | 102.65 |
| v2 | de Belote v2 | 29/100 | 21–38% | 194/598 (32.4%) | 152/194 (78.4%) | 98.51 |
| v2 | de Belote v3 | 26/100 | 19–33% | 201/609 (33%) | 155/201 (77.1%) | 98.66 |

V2-minus-v1 win differences are −26 percentage points against de Belote v2
(95% paired-seed interval −36 to −16) and −22 against v3 (−32 to −11).
Both Brooklyn versions use the same card play; their bidding differs.
V2's conditional success is similar, but it contests far fewer auctions.
These observations do not justify blindly raising every v2 contract.

## Before versus after winning-card correction

| Brooklyn / opponent | Wins before → now | Change (pp) | 95% paired interval (pp) | Contract success before → now |
| --- | ---: | ---: | --- | ---: |
| v1 / de Belote v2 | 55 → 55 | 0 | -7 to 8 | 80.6 → 78.7% |
| v1 / de Belote v3 | 47 → 48 | +1 | -4 to 6 | 78.4 → 78.4% |
| v2 / de Belote v2 | 31 → 29 | -2 | -9 to 5 | 78.8 → 78.4% |
| v2 / de Belote v3 | 22 → 26 | +4 | -1 to 10 | 78.1 → 77.1% |

All four before/after intervals include zero. This sample does not establish
an improvement or regression; it also does not establish equivalence. The
two playing changes (risk-aware fallback and removal of last-seat economy)
were benchmarked together, not separately.

## Calibration — both views

Margin = trick points + dix de der + belote − numeric bid, excluding awarded
contract/coinche bonuses. Failures remain in both views. Success is not
necessarily equivalent to a nonnegative margin because the scoring engine
also checks its majority condition. No explicit Capot contracts were bid.

| Brooklyn / opponent | All N | Mean margin, capots included | Capot deals | Ordinary N | Mean margin, no capots | Ordinary median | Ordinary SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 / de Belote v2 | 305 | +29.52 | 27 | 278 | +17.70 | 18 | 22.46 |
| v1 / de Belote v3 | 306 | +31.18 | 31 | 275 | +17.67 | 19 | 22.65 |
| v2 / de Belote v2 | 194 | +27.08 | 15 | 179 | +16.73 | 19 | 22.21 |
| v2 / de Belote v3 | 201 | +25.92 | 15 | 186 | +15.75 | 19 | 23.18 |

Only the separately labelled ordinary-margin view excludes capots, whose
special dix-de-der bonus inflates the all-deal margin. They are never removed
from wins, taking or contract success. Mean ordinary cushions around 16–18
points do not by themselves imply good bidding, given failures and contracts
conceded to opponents. Detailed bid/opening groups, margin distributions,
opponent rows and trump-leading counts are retained in the saved JSON.

## Reproduce and inspect

See [benchmark instructions](README.md), the
[previous snapshot](2026-10-20-ace-preservation.md), and
[saved results](results-2026-10-20-risk-aware-winners.json). The saved summary
includes all eight bot-side rows and 400 seed/seat game outcomes, enabling
paired comparisons. Full per-game deal records were also generated by:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --pairs 50 --workers 4 --output results.json
```
