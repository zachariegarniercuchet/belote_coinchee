# Brooklyn SA bidding — 30 October 2026

Paired before/after comparison: 800 complete games per policy (1,600 total). All four Brooklyn versions face de Belote v2 and v3, 100 games per matchup. No parameter was retuned after looking at outcomes.

SA contracts are selected more strictly and made more often in all four versions.
V4 moves from 132/194 (68.0%) to 79/100 (79.0%) made SA contracts; ordinary mean
margin rises from 6.01 to 10.66. Overall taking falls from 52.7% to 49.6%, and wins
rise from 113/200 to 120/200. The paired win difference is +3.5 percentage points,
95% interval [-0.5, 8.0]: this sample does not establish a reliable overall win gain.
The selection change is substantial: roughly half as many SA declarations.
Mean SA bids rise despite fewer takes; both selection and the new partnership
credits affect these figures, and their separate contributions were not isolated.

## Frozen policy change

- SA subtracts 10 per void, 4 per singleton without an ace, and 2 per other suit without an ace, guarded ten, or at least third king. Five immediate masters halve these penalties. A consecutive sequence of at least seven masters waives them when the bot itself has the opening lead.
- The seven-card waiver has a point bound: after seven winning leads each opponent has only one card left; across every possible eighth card in our hand, at least 85 SA card points have already been secured. Five or six master cards in one suit with weak side cards can leave only 53 or 65 card points respectively.
- Retained protected SA tens and at least third kings are valued at 65% rather than 55%; immediate masters stay at 85%. Opening still needs a value of 30 for 80, then another 10 per level. Three stopped suits can also qualify a regular hand without two immediate masters. These are heuristic parameters, not probabilities.
- Partner support adds +10 per exactly second ten without its ace and +10 per pair of at least third kings not already counted in a master sequence. Existing prefix credits remain; all contributions are spent once.
- TA evaluation/support and suited policies are unchanged; a 1,000-hand audit matched all three TA evaluation functions exactly. Their observed game results can still change through different auctions and subsequent deals.
- The reported hand (spades 10/K/9, hearts Q/7, clubs A/10/8, diamonds void) moves from 32.35 to 21.75 estimated SA points, and no longer opens SA.

## SA contracts — both opponents pooled

Each cell shows before → after. Success includes capots and the strict majority condition. Ordinary margins exclude achieved capots only.

| Brooklyn | SA taken | SA take share | SA made / taken | Success | Mean bid | Ordinary mean margin |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| brooklyn_v1 | 129 → 77 | 10.3% → 6.2% | 100/129 → 67/77 | 77.5% → 87.0% | 100.23 → 104.81 | 8.98 → 13.75 |
| brooklyn_v2 | 178 → 91 | 14.5% → 7.4% | 120/178 → 79/91 | 67.4% → 86.8% | 101.52 → 104.84 | 6.01 → 15.33 |
| brooklyn_v3 | 192 → 97 | 15.4% → 7.9% | 131/192 → 78/97 | 68.2% → 80.4% | 100.05 → 105.36 | 6.13 → 11.88 |
| brooklyn_v4 | 194 → 100 | 15.5% → 8.1% | 132/194 → 79/100 | 68.0% → 79.0% | 100.10 → 105.30 | 6.01 → 10.66 |

## Overall outcomes

| Brooklyn | Wins / 200 | Taking | All contracts made | Win change, 95% interval (pp) |
| --- | --- | --- | --- | --- |
| brooklyn_v1 | 112 → 108 | 58.2% → 55.8% | 79.7% → 81.0% | -2.0, [-7.0, 2.5] |
| brooklyn_v2 | 79 → 80 | 48.6% → 45.1% | 72.6% → 78.3% | +0.5, [-3.5, 5.0] |
| brooklyn_v3 | 113 → 118 | 52.9% → 49.6% | 80.4% → 84.3% | +2.5, [-2.0, 7.0] |
| brooklyn_v4 | 113 → 120 | 52.7% → 49.6% | 80.4% → 84.3% | +3.5, [-0.5, 8.0] |

## SA success uncertainty

| Brooklyn | Success change (pp) | Paired 95% interval (pp) |
| --- | ---: | --- |
| brooklyn_v1 | +9.5 | [2.03, 16.89] |
| brooklyn_v2 | +19.4 | [10.93, 28.65] |
| brooklyn_v3 | +12.2 | [3.9, 20.1] |
| brooklyn_v4 | +11.0 | [2.24, 19.12] |

## Ordinary SA margins

Earned points minus the numeric contract, excluding achieved capots. Before → after. A nonnegative margin can still fail the strict majority condition.

| Brooklyn | Below bid | 0–9 above | 10–20 above | Over 20 above |
| --- | --- | --- | --- | --- |
| brooklyn_v1 | 23.6% → 13.7% | 18.7% → 19.2% | 26.0% → 27.4% | 31.7% → 39.7% |
| brooklyn_v2 | 34.5% → 14.1% | 13.1% → 21.2% | 22.6% → 21.2% | 29.8% → 43.5% |
| brooklyn_v3 | 33.5% → 21.1% | 16.5% → 20.0% | 22.0% → 21.1% | 28.0% → 37.8% |
| brooklyn_v4 | 33.7% → 22.6% | 16.3% → 19.4% | 22.3% → 21.5% | 27.7% → 36.6% |

## Wins by opponent

| Brooklyn | Opponent | Before / 100 | After / 100 |
| --- | --- | ---: | ---: |
| brooklyn_v1 | spark_v2 | 58 | 55 |
| brooklyn_v1 | spark_v3 | 54 | 53 |
| brooklyn_v2 | spark_v2 | 39 | 42 |
| brooklyn_v2 | spark_v3 | 40 | 38 |
| brooklyn_v3 | spark_v2 | 54 | 57 |
| brooklyn_v3 | spark_v3 | 59 | 61 |
| brooklyn_v4 | spark_v2 | 56 | 58 |
| brooklyn_v4 | spark_v3 | 57 | 62 |

## Protocol and limitations

- Reproduce on each named revision with `python -B benchmarks/bots.py --brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3 brooklyn_v4 --pairs 50 --seed 46000 --workers 4 --output results.json`.
- Before: `6d2270d6407e3cedd3dcc844e23bb1cecd0331ba`. After: `e27e94771cad703236be9b07c1e460ae07930502`.
- Runtime: before 1394.5s; after 1190.7s. Four workers per run.
- Seeds 46000–46049, each replayed with Brooklyn on both teams, dealer `seed % 4`, bot RNG `seed * 17 + seat`, target 1000, web engine. Display sleeps/broadcasts disabled; the running server is not contacted or restarted.
- Confidence intervals use 4,000 paired bootstrap resamples of whole seed clusters, fixed RNG 20261030. Each cluster includes both opponents and both team swaps. Games and deals inside a cluster are not treated as independent.
- The final policy was frozen before its run. An initial 800-game candidate run at 18f1961 was superseded after a deductive five/six-card counterexample tightened the long-run waiver to seven; its outcomes were not inspected to select parameters and are not mixed into this comparison.
- These fresh seeds were not used to tune the parameters. Matching seeds does not keep later hands identical: different auctions/game lengths change subsequent random draws. This comparison measures both selection and support changes together, not their separate effects.
- Capots are included in wins, taking, success and scores. Explicit Capot bids have no numeric margin. Numeric margins include belote/dix-de-der, excluding awarded contract/double bonuses.
- All 800 record keys per policy were checked for uniqueness, pairing and complete matchups; summary counts were recomputed from raw records. No failed contract or capot was dropped.
- The existing SA/TA parity test now assigns the same player dictionary to the session and engine, as production does; the newly pulled notification dispatcher uses `session.players`.

Raw data: [before](results-2026-10-30-sa-before.json), [after](results-2026-10-30-sa-after.json), [comparison](sa-comparison-2026-10-30.json), [fixed-hand selection audit](sa-shape-audit-2026-10-30.json).
