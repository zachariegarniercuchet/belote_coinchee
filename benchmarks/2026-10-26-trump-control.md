# Attacking Brooklyn: weakest winning trump — 26 October 2026

## Implemented correction

Frozen source `8f023422da6c26a4e671b839c5baa02846fe0201`. All three Brooklyn versions now take
with the weakest legal winning trump when attacking, in EVERY seat, including
last. With J/R and R sufficient to win, use R and preserve J. The same applies
to cutting a side suit. Following-suit/compulsory-overtrump legality still
comes from the engine; the existing safe-partner feeding priority is unchanged.

This replaces the shared point-first trump winner policy. Non-trump winner
selection, defence, bidding and lead selection are unchanged, including v3's
last-trump lead exception. This rule chooses a CURRENT winner; before last
seat it does not promise immunity from a later overtrump.

The existing three Brooklyn journey tests were extended, not multiplied:
J/R in second/third/last seat and the supplied 80-heart example. Brooklyn,
autoplay and claim suites pass (33 functions). No browser verification was
performed; no frontend code changed.

## Supplied 80-heart deal

The [recorded deal and legal replays](replay-2026-10-26-80-hearts.json)
preserve all 32 supplied cards and the 80-heart contract by Nora, seat 1.
Seats 1/3 attack, 0/2 defend. There is no belote.

A targeted regression uses only these supplied cards: Octave leads 7-heart,
the human partner must play 8-heart, Charles discards 7-club. Nora must take
Q-heart rather than J-heart, then lead J-heart from J/10 on the next trick.
This now passes for v1/v2/v3.

Full-deal illustrations explore all four possible opening leaders against
de Belote v3, with fixed per-seat RNG `20261026 + seat`. The human's seat
is replaced by the SAME Brooklyn version as Nora. They are NOT a reconstruction
of the user's moves, and NOT an optimal-play or guaranteed-contract proof.
One v1/v2 illustration starting at seat 3 legally makes 83 points. Other
illustrations fail; none establishes that the actual observed loss was caused
solely by the old largest-winning-trump rule.

The four opposing hearts (9/A/K/7 concentrated in one defender) and the
defender's club ace make control and timing important. A winning illustrative
line is not evidence that 80 cannot fall against different defence.
These replays also do not identify the cause of the earlier reported failure
to LEAD trumps with two-plus trumps: that issue remains unconfirmed. Do not
conflate a corrected taking rule with a diagnosed failure to draw on lead.

## Full-game validation protocol

600 NEW full games: all three Brooklyn versions versus de Belote v2/v3,
100 per matchup, target 1000. Seeds 30000–30049, each replayed on teams 0/1.
Dealer `seed % 4`, bot RNG `seed * 17 + seat`. Current web engine, normal
bot settings, display sleeps/broadcasts disabled. Runtime
7.6 minutes. V1/v2 were rerun because the shared
playing policy changed; their old results were NOT reused as current results.

All 600 unique game keys, both swaps per seed, wins, played-deal totals,
declarations and successes reconcile to raw records. No dropped games or
outcome exclusions. Bidding fixed; no tuning during or after the run.
No push, running-server restart or live-room changes.

These are reused development seeds, not holdout validation. Different play
changes subsequent game lengths/hands/contracts, so matched-seed comparisons
are not identical fixed-contract replays. No universal ranking claim follows.

## Results — capots included

Taking excludes cancelled deals only. Success is the engine's actual flag,
including majority. All capots and full scores count in wins, taking,
contract success and target-score progression.

| Brooklyn | Opponent | Wins | Win 95% interval | Taking | Contracts made | Mean bid |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| v1 | de Belote v2 | 52/100 | 44–60% | 297/595 (49.9%) | 230/297 (77.4%) | 102.56 |
| v1 | de Belote v3 | 49/100 | 41–56% | 301/605 (49.8%) | 240/301 (79.7%) | 102.59 |
| v2 | de Belote v2 | 32/100 | 23–41% | 195/602 (32.4%) | 154/195 (79%) | 98.56 |
| v2 | de Belote v3 | 28/100 | 20–36% | 201/607 (33.1%) | 159/201 (79.1%) | 98.71 |
| v3 | de Belote v2 | 45/100 | 38–52% | 234/594 (39.4%) | 204/234 (87.2%) | 101.97 |
| v3 | de Belote v3 | 46/100 | 36–55% | 235/603 (39%) | 203/235 (86.4%) | 102.21 |

## Before → after

V1/v2 references: `7fc077f` in the
[risk-aware winner snapshot](2026-10-20-risk-aware-winners.md).
V3 reference: `75720f0` in the
[recoverable-card snapshot](2026-10-21-recoverable.md).

Approximate 95% percentile-bootstrap intervals use 4,000 resamples of whole
seed pairs, preserving correlated swaps and before/after matching. No normality
assumption or hypothesis-test p-values. Pointwise exploratory intervals,
not multiplicity-adjusted tests.

| Brooklyn / opponent | Wins before → now | Difference (pp) | 95% paired interval (pp) | Contract success before → now |
| --- | ---: | ---: | --- | ---: |
| v1 / de Belote v2 | 55 → 52 | -3 | -10 to 4 | 78.7 → 77.4% |
| v1 / de Belote v3 | 48 → 49 | +1 | -6 to 8 | 78.4 → 79.7% |
| v2 / de Belote v2 | 29 → 32 | +3 | -3 to 9 | 78.4 → 79% |
| v2 / de Belote v3 | 26 → 28 | +2 | -3 to 7 | 77.1 → 79.1% |
| v3 / de Belote v2 | 46 → 45 | -1 | -8 to 6 | 85.2 → 87.2% |
| v3 / de Belote v3 | 42 → 46 | +4 | -2 to 11 | 83.9 → 86.4% |

All six before/after win intervals include zero. The correction implements
the requested trump-control policy; this sample does not establish a general
win-rate improvement or regression. No parameters were changed in response.

## Calibration — both views

Margin = trick points + dix de der + belote − numeric bid, excluding awarded
contract/coinche bonus. Failures remain in both views. Majority means a
nonnegative margin does not always imply success. All contracts were numeric.

| Brooklyn / opponent | All N | Mean margin, capots included | Capot deals | Ordinary N | Mean margin, no capots | Ordinary median | Ordinary SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 / de Belote v2 | 297 | +29.08 | 25 | 272 | +17.96 | 18 | 23.02 |
| v1 / de Belote v3 | 301 | +29.48 | 26 | 275 | +18.04 | 19 | 22.76 |
| v2 / de Belote v2 | 195 | +27.28 | 15 | 180 | +16.99 | 19 | 22.15 |
| v2 / de Belote v3 | 201 | +23.74 | 12 | 189 | +15.65 | 19 | 22.66 |
| v3 / de Belote v2 | 234 | +31.96 | 20 | 214 | +21.49 | 23.5 | 19.10 |
| v3 / de Belote v3 | 235 | +29.47 | 15 | 220 | +21.80 | 22 | 19.36 |

Only the ordinary-margin view excludes capots, whose special dix-de-der bonus
inflates the all-deal mean. They are never removed from outcome rates.
Detailed bid/opening groups and actual lead-choice metrics remain in the JSON.

## Reproduce

[Saved results](results-2026-10-26-trump-control.json) include all 12 bot-side
rows, 600 paired game outcomes and six before/after comparisons. Full optional
output also retains all per-game deal records:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3 --pairs 50 --workers 4 --output results.json
```

See [benchmark instructions](README.md) and
[current Brooklyn policy](../belote/bots/BROOKLYN.md).
