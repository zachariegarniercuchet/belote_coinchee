# Brooklyn v3 recoverable-card evaluation — 21 October 2026

Implemented a different valuation scale rather than lowering the old Spark
thresholds. Contract success improves from 68–70% to 84–85% on this sample,
but taking falls from about 52% to 39–40%. Wins are 46/100 and 42/100. There
is no clear full-game win improvement over the previous hybrid yet.

## Policy frozen before running

Source `75720f0b85db790a4ec1022a6c868c9f41100351`:

- Evaluate survivors after sacrificing weak cards to absent higher honours.
  Side 10/K/Q loses Q, retaining prospective 10/K; side K/Q retains nothing.
  Missing J above trump 9/A/10 consumes 10, not all three credited as winners.
- Survivors earn actual own-card points, not arbitrary +5 per trump. Trump
  confidence J+9/J/9/neither: 0.95/0.85/0.75/0.55. Side confidence:
  0.90 with J+9; 0.85 with J and four-plus trumps; 0.80 with J;
  0.75 with 9; 0.65 with neither.
- Established side winners get a 0.7 entry factor. This applies per card:
  an immediately master ace is not penalized because a lower card is lost.
  These factors are explicit initial heuristics, not fitted win probabilities.
- Own belote adds its actual 20 once. Voids add 3 per prospective cut,
  limited to spare trumps after reserving max(3, 8 - trump count) for drawing,
  and only with J. Thus no automatic void credit with three/four trumps.
- At least three trumps; exactly three require J or 9. Recoverable scores
  30/40/50/60/70 map to 80/90/100/110/120. New scale, not the old score.
  The reported 9/A/10 + 10/K/Q + K/Q + void example scores 26.10 at spades
  and passes the opening auction in every suit.
- Partner support still uses +10 per trump J/9 and side ace, +20 belote,
  spent once from the last TEAM bid. No second own-hand entry/rebid bonus.
  Coinche/surcoinche still use the separate old Spark evaluation.
- V3 no longer hunts with its last trump when a side lead is available.
  Forced plays remain legal. V1/v2 and default bot unchanged.
- Existing three Brooklyn journey tests extended, not multiplied. Full seeded
  console/web parity, auction-credit accounting, example-hand rejection and
  last-trump behavior pass; autoplay/claim/lobby suites also pass (34 total
  test functions across these selected suites).

## Protocol and validation

200 NEW full games: 100 per opponent, target 1000, seeds 30000–30049, each
played with Brooklyn on team 0/1. Dealer `seed % 4`; bot RNG
`seed * 17 + seat`. Current web engine, normal bot settings; display sleeps
and broadcasts disabled. Runtime 2.1 minutes.

Every game completed, all 200 unique game keys and both seat swaps verified.
Wins, declarations, successes, cancelled deals and played totals reconcile
with raw records. No excluded outcomes or tuning after seeing the run.
The local server was not restarted; no live rooms changed and nothing pushed.

Reference policies are saved, not newly simulated here:
[previous v3](2026-10-20-hybrid.md) at `7b3c7d26441b4c09cf0cce7947420b5f27506f1a`;
[v1/v2](2026-10-20-risk-aware-winners.md) at
`7fc077f9d733cde168dbc84bbfbd9a9c88713018`. Same seeds/settings; v1/v2 unchanged.

Reused development seeds are not a holdout. Different play and bidding change
game lengths and later contracts; these are not identical fixed-hand replays.
Both the new evaluator and last-trump behavior changed together; this run
cannot attribute effects to either in isolation.

## Before → after — capots included

Taking excludes cancelled deals only. Contract success is the engine's
actual contract-reached flag including majority. All capots count in wins,
taking, success, awarded scores and target progression.

| Opponent | Wins | Taking | Contracts made | Mean bid |
| --- | ---: | ---: | --- | ---: |
| de Belote v2 | 42 → 46/100 | 51.7 → 39.7% | 210/309 (68%) → 202/237 (85.2%) | 112.85 → 102.07 |
| de Belote v3 | 42 → 42/100 | 51.7 → 39.2% | 220/314 (70.1%) → 198/236 (83.9%) | 112.17 → 102.08 |

Safety improved in observed conditional outcomes, but greater selectivity
cost roughly 12 percentage points of taking. This does not yet meet both
aims of taking very often AND virtually never falling. It is not justified
to present the revised policy as a proven overall upgrade.

## Paired win differences

Approximate 95% percentile-bootstrap intervals use 4,000 resamples of whole
seed pairs, preserving swap dependence and before/after matching. No normality
assumption or hypothesis-test p-values. Pointwise exploratory intervals,
not multiplicity-adjusted tests or fresh-seed validation.

| New v3 minus reference | Common opponent | Difference (pp) | 95% paired interval (pp) |
| --- | --- | ---: | --- |
| previous_v3 | de Belote v2 | +4 | -7 to 16 |
| v1 | de Belote v2 | -9 | -20 to 2 |
| v2 | de Belote v2 | +17 | 6 to 27 |
| previous_v3 | de Belote v3 | 0 | -13 to 13 |
| v1 | de Belote v3 | -6 | -17 to 5 |
| v2 | de Belote v3 | +16 | 4 to 28 |

Neither before/after interval excludes zero; neither comparison with v1 does.
Comparisons with v2 favor the new policy on this development sample. These
are outcomes versus common opponents, not direct head-to-head matches.

## Calibration and remaining weak groups

Margin = trick points + dix de der + belote − numeric bid. No awarded
contract/coinche bonus; failures remain included. The majority condition
means nonnegative margin is not always contract success.

| Opponent | All N | Mean margin, capots included | Capot deals | Ordinary N | Mean margin, no capots | Ordinary median | Ordinary SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| de Belote v2 | 237 | +32.02 | 22 | 215 | +20.35 | 23 | 19.03 |
| de Belote v3 | 236 | +30.61 | 19 | 217 | +20.68 | 21 | 20.89 |

Only the labelled ordinary-margin view excludes capots, whose special
dix-de-der bonus inflates the all-deal mean. No outcome rates exclude them.
Every contract in this run was numeric; no explicit Capot bids.

Across both opponents, by FINAL bid (not necessarily the opening bid):

| Bid | Made / contracts | Success |
| --- | ---: | ---: |
| 80 | 15/29 | 51.7% |
| 90 | 91/112 | 81.3% |
| 100 | 124/147 | 84.4% |
| 110 | 113/127 | 89.0% |
| 120 | 38/39 | 97.4% |
| 130 | 13/13 | 100.0% |
| 140 | 6/6 | 100.0% |

The 80 group is still fragile (15/29); three-trump nine-without-jack openings
make 14/23 contracts. Small, selected groups, not controlled causal estimates.
High-bid groups contain stronger hands and partner support, so their success
does not justify raising all hands or indiscriminately lowering thresholds.
No extra tuning was performed on these results.

## Reproduce

[Saved results](results-2026-10-21-recoverable.json) retain four new bot-side
rows, saved reference rows, all 200 new game outcomes and six paired
comparisons. Reference outcomes remain in their linked JSON snapshots.
Full optional output also retains every deal record:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --brooklyn brooklyn_v3 --pairs 50 --workers 4 --output results.json
```

See [benchmark instructions](README.md) and
[current strategy](../belote/bots/BROOKLYN.md).
