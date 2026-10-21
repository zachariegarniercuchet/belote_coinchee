# Brooklyn v2 qualified openings — benchmark, 20 October 2026

Frozen before the later shared Brooklyn ace-preservation/partner-feeding fix.
The results below include capots in wins, taking and contract success; only
the explicitly labelled ordinary-deal margin table excludes capot deals.

The latest amendment makes accepted contracts safer, but takes far fewer
contracts and does not improve observed game wins. This is not a card-play
change: v1 and v2 still share the exact same playing policy.

## Frozen policy and method

- Source: `865e23aa4a3ce80d6dde9b2f67aaaebbc2d92ef0`.
- New v2: at least three trumps with J or 9, plus a side ace OR two dix seconds.
  First side ace included in the 80 base; both J/9 add 10, each extra side ace
  adds 10. Belote counts on entry (+10 with three trumps, +20 with four or more).
  A new suit can be independently proposed without transferring old credits.
  Void/tens bonuses stay at rebidding; trump ace earns no separate credit.
- 400 full games, target 1000, 100 per matchup. Seeds 30000–30049,
  each with Brooklyn on teams 0 and 1; dealer `seed % 4`, bot RNG `seed*17+seat`.
  Current web engine, normal search settings, display sleeps/broadcasts disabled.
  Runtime 4.3 minutes; running server untouched.
- All games completed, all seed swaps and aggregation totals checked. The
  unchanged v1 rows match the preceding benchmark exactly, not just win counts.
- Approximate 95% win intervals: percentile bootstrap of whole seed pairs,
  4,000 resamples. Do not count correlated games/deals as independent trials.
  Intervals are pointwise and exploratory, not a simultaneous ranking test.
- No tuning during or after the run. Same development seeds as before, NOT an
  independent holdout. Different bidding changes later deals and game lengths;
  matching seeds does not fix every subsequent hand or contract.

## Current results

Taking excludes cancelled deals. Success is conditional on declaring and uses
the scoring engine's actual flag, including its majority requirement.

| Brooklyn | Opponent | Wins | Win interval | Taking | Contracts made | Mean bid |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| v1 | de Belote v2 | 53/100 | 45–62% | 306/604 (50.7%) | 240/306 (78.4%) | 102.35 |
| v2 | de Belote v2 | 24/100 | 16–32% | 198/616 (32.1%) | 143/198 (72.2%) | 98.48 |
| v1 | de Belote v3 | 50/100 | 42–58% | 313/622 (50.3%) | 242/313 (77.3%) | 102.52 |
| v2 | de Belote v3 | 19/100 | 11–28% | 199/611 (32.6%) | 149/199 (74.9%) | 98.84 |

V2 minus v1 win-rate differences: −29 percentage points against de Belote v2
(95% paired-seed interval −40 to −18), and −31 against v3 (−40 to −21).
These matchups still favour v1 substantially.

## Comparison with the immediately preceding v2

Previous source: `edbd52e639faa9132ce7036fbc4b6014acacf718`. That policy included the
trump-ace/belote/void corrections but still locked suits and reserved aces for
rebidding, without the new side-strength opening requirement.

| Opponent | Wins before → now | Taking before → now | Made / taken before → now | Success before → now |
| --- | ---: | ---: | --- | ---: |
| de Belote v2 | 31 → 24 | 47.4 → 32.1% | 186/282 → 143/198 | 66.0 → 72.2% |
| de Belote v3 | 23 → 19 | 48.1 → 32.6% | 188/295 → 149/199 | 63.7 → 74.9% |

New-minus-previous win differences are −7 percentage points against de Belote
v2 (paired-seed interval −16 to +2) and −4 against v3 (−14 to +6). Those intervals
include zero: do not claim a demonstrated population-level decline from the
previous v2 on this sample. However, there is no observed win improvement, and
the updated v2 still trails v1 clearly.

The higher conditional success rate comes with FEWER successful attacking deals:
186→143 and 188→149. The changes improve safety when bidding, but concede more
contracts. De Belote takes the other 67–68% of played deals. Its v2 version
makes 332/418 (79.4%) contracts; its v3 version makes 345/412 (83.7%).
The effects of individual changes (qualification, base valuation, suit switches)
are not isolated by this combined-policy comparison.

## Calibration

Margin = earned trick points + dix de der + belote − numeric bid, not awarded
contract/coinche bonuses. Capot deals are excluded here; failures stay included.

| Bot / opponent | N | Mean margin | Median | SD | Margin 10–20 above bid |
| --- | ---: | ---: | ---: | ---: | ---: |
| Brooklyn v1 / de Belote v2 | 286 | +17.40 | +17 | 22.36 | 19.6% |
| Brooklyn v2 / de Belote v2 | 189 | +13.90 | +17 | 22.93 | 19.0% |
| Brooklyn v1 / de Belote v3 | 289 | +15.57 | +16 | 22.45 | 18.0% |
| Brooklyn v2 / de Belote v3 | 189 | +13.98 | +18 | 22.87 | 19.0% |

V2 now earns about 14 points above its bid on average outside capots, much closer
to the tentative 10–20-point cushion. Nevertheless, it still fails 25–28% of
contracts and takes only about one-third of played deals. A good average margin
does not by itself imply a good overall bidding policy. On failed contracts,
mean opponent-minus-Brooklyn awarded-score gaps are 286.91 / 291.40 points
against de Belote v2 / v3.

## Exploratory opening diagnostic

Pooled across the two opponents. This is the ORIGINAL opener's holding in the
final team-suit episode, not necessarily the last bidder. Counts are descriptive
and correlated, not a causal attribution to any single card.

| Opening trump holding | Contracts made | Rate |
| --- | ---: | ---: |
| Exactly 3, nine without jack | 41/91 | 45.1% |
| Exactly 3, jack without nine | 86/112 | 76.8% |
| Exactly 3, both jack and nine | 53/61 | 86.9% |
| At least 4, any qualifying honours | 112/133 | 84.2% |

Three-trump nine-only contracts remain weak despite the added side-strength
condition. The stricter entry condition also excludes hands previously allowed;
higher success alone does not show that all such passes are beneficial.
No policy adjustment was made after these observations.

Brooklyn v2 again led trump on every measured attacking opportunity (371/371
and 387/387): both trump and side choices were available and opponents actually
held trump. Forced/claimed/automatic-last-trick plays are excluded. This is a
behavioural descriptor, not evidence that always drawing trump is optimal.

## Reproduce and inspect

See [README.md](README.md) and
[results-2026-10-20-qualified-openings.json](results-2026-10-20-qualified-openings.json).
The JSON retains all eight side-specific summaries, bid/opening breakdowns and
400 game outcomes for paired-win interval checks.

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --pairs 50 --workers 4 --output results.json
```

The optional full output retains the per-game deal records behind the summary.
