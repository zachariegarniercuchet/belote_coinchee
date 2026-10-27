# Brooklyn v3: first trump lead and return to partner — 26 October 2026

V3 wins 46/100 games against each opponent, versus 45/100 and 46/100 in the
immediately preceding snapshot. There is no clear full-game gain on this
sample. Contract success falls slightly; taking remains around 39–40%.

## Frozen policy

Source `feb956d1c104a4a0302af4e5d015361867e7773e`. V3 now leads its singleton trump before
the first trump lead, and returns trumps when partner was the first team
bidder in that suit. No late-deal/card-count threshold.

The first team bidder is captured from public auction history at accepted
contract notification, including earlier announcements before suit switches.
It is not inferred from the final bidder. A separate public flag records an
actual trump LEAD; a cut alone does not establish that drawing has begun.
Both reset each deal.

Only after drawing has begun, and absent that return-to-partner condition,
can v3 preserve its single trump instead of leading it. The base policy still
stops drawing if public information proves opponents out of trumps.
The reported Nora 7-heart and ace-diamond hands now lead trump in the existing
representative tests. Partner returns after an earlier trump round and
next-deal resets are covered too; still three Brooklyn test functions.

Attacking weakest-winning-trump selection is retained. Bidding, v1/v2 and
the default bot are unchanged. No browser verification, push, running-server
restart or live-room changes.

## Protocol and validation

200 NEW full games: 100 per opponent, target 1000, seeds 30000–30049, each
played on team 0/1. Dealer `seed % 4`, bot RNG `seed * 17 + seat`. Current
web engine, normal bot settings, display sleeps/broadcasts disabled. Runtime
2.25 minutes.

All games completed. All 200 unique game keys, both swaps, win totals,
declarations, successes, cancelled and played-deal counts reconcile to raw
records. No outcome exclusions, silent dropped games or tuning after results.

References are the [preceding 600-game snapshot](2026-10-26-trump-control.md)
at `8f023422da6c26a4e671b839c5baa02846fe0201`: v1/v2 are unchanged saved
baselines, not newly simulated here. These compare versions versus common
opponents, NOT direct head-to-head games.

Reused development seeds are not a holdout. Changed card play changes game
lengths and subsequent hands/contracts; paired seeds do not make these
fixed-hand or fixed-contract replays.

## Outcomes — capots included

Taking excludes cancelled deals only. Success is the actual engine flag,
including majority. Every capot and full score counts in wins, taking,
contract success and target progression.

| Opponent | Wins before → now | Taking before → now | Contracts made before → now | Mean bid before → now |
| --- | ---: | ---: | --- | ---: |
| de Belote v2 | 45 → 46/100 | 39.4 → 39.6% | 204/234 (87.2%) → 199/233 (85.4%) | 101.97 → 101.85 |
| de Belote v3 | 46 → 46/100 | 39 → 39.5% | 203/235 (86.4%) → 201/238 (84.5%) | 102.21 → 101.93 |

The observed conditional contract-success changes are not controlled same-hand
effects: the selected contracts and later deals also change. Mean bids remain
near 102; there was no bidding adjustment in response to results.

## Paired win comparisons

Approximate 95% percentile-bootstrap intervals use 4,000 resamples of whole
seed pairs, retaining dependent swaps and matched references. No normality
assumption or hypothesis-test p-values. Pointwise exploratory intervals,
not multiplicity-adjusted rankings.

| New v3 minus reference | Common opponent | Difference (pp) | 95% paired interval (pp) |
| --- | --- | ---: | --- |
| Brooklyn v3 | de Belote v2 | +1 | -3 to 6 |
| Brooklyn v1 | de Belote v2 | -6 | -18 to 6 |
| Brooklyn v2 | de Belote v2 | +14 | 2 to 26 |
| Brooklyn v3 | de Belote v3 | 0 | -5 to 5 |
| Brooklyn v1 | de Belote v3 | -3 | -15 to 9 |
| Brooklyn v2 | de Belote v3 | +18 | 6 to 30 |

Both before/after v3 intervals include zero, as do comparisons with v1.
Comparisons with v2 favor current v3 on this development sample. No demonstrated
overall improvement from the singleton correction should be claimed.

## Lead choices — explicitly mixed contexts

Among actual attacking lead choices with both a trump and side card available,
while an opponent REALLY held trump:

| Opponent | Trump leads before | Trump leads now |
| --- | ---: | ---: |
| de Belote v2 | 359/486 (73.9%) | 375/452 (83%) |
| de Belote v3 | 345/476 (72.5%) | 375/462 (81.2%) |

These counts include the still-permitted single-trump preservation AFTER a
trump round when the bot is not returning partner's opening suit. They must
not be interpreted as missed hunts with TWO-plus trumps, or as a causal
measurement of drawing's value. Hidden hands are inspected only AFTER the
choice for diagnostics, never passed to bots. Changing contract selection and
game lengths changes these denominators; this is not a fixed-context replay.

## Calibration — both views

Margin = earned trick points + dix de der + belote − numeric bid. No awarded
contract/coinche bonus; failures remain. Majority means nonnegative margin
does not necessarily imply success. All contracts in this run were numeric.

| Opponent | All N | Mean margin, capots included | Capot deals | Ordinary N | Mean margin, no capots | Ordinary median | Ordinary SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| de Belote v2 | 233 | +32.89 | 21 | 212 | +21.94 | 26 | 19.71 |
| de Belote v3 | 238 | +28.59 | 16 | 222 | +20.42 | 22 | 20.16 |

Only the separately labelled ordinary-margin view excludes capots, whose
special dix-de-der bonus inflates the all-deal mean. Outcome rates never do.

## Reproduce

[Saved results](results-2026-10-26-first-trump.json) retain all four new bot-side
rows, six reference Brooklyn rows, all 200 new outcomes and six paired
comparisons. Full optional output retains per-game deal records:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --brooklyn brooklyn_v3 --pairs 50 --workers 4 --output results.json
```

See [benchmark instructions](README.md) and
[current Brooklyn policy](../belote/bots/BROOKLYN.md).
