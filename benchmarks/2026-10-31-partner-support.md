# Brooklyn vs de Belote — campaign started 31 October 2026

800 complete games at the final policy revision, on fresh seeds 48000–48049. Brooklyn v1–v4 each face de Belote v2 and v3 in 100 games per matchup, with teams reversed.

V4 wins 51/100 against de Belote v2 and 48/100 against v3, or 99/200 overall
(49.5%, seed-cluster 95% interval 41.0–58.0%). Its suited contracts succeed
360/409 times (88.0%), TA 64/83 (77.1%), and SA 89/135 (65.9%). SA remains
the least reliable mode on this fresh sample, with an ordinary mean cushion
of 4.49 points. The earlier SA result of 79.0% did not generalize to this lot;
different seeds and suited support/selection prevent attributing the change
solely to the new trump-void deduction.

V1 declares suited contracts on 43.5% of played deals versus V4's 32.9%, and
makes them 82.2% versus 88.0%. Its overall win rate is 53.5% versus 49.5%.
The paired V1-minus-V4 difference is +4.0 percentage points, 95% interval
[-3.5, 12.5], so the ranking is uncertain. Their card play and mode selection
also differ. V4's 23.88-point ordinary suited margin suggests scope to
investigate higher supported suited bids; this benchmark does not isolate
that change from accepting more marginal hands or changing card play.

## Current rule and validation

- Suited partnership support v2/v3/v4 loses 10 when the supporter has no trump in the partner's suit, floored at zero. Apply once to the hand's total credit before deducting previous raises; reset with the suit episode. Independent openings and SA/TA budgets keep their own policies. V1 already needs three trumps to support. The revised SA shape/protected-honour policy is included.
- Two side aces and no trump support +10; one ace and no trump supports zero. Holding one trump keeps the ordinary credit. Repeated turns cannot spend the same credit twice.
- Existing Brooklyn and SA/TA nominal journeys passed (five test methods, extended without adding test methods), including full console/web games, contract notification, resets and partnership credit accounting.

## Direct matchups

| Brooklyn | de Belote | Wins / 100 | Win 95% interval | Taking | Contracts made |
| --- | --- | ---: | --- | ---: | --- |
| brooklyn_v1 | spark_v2 | 56 | [48.0, 64.0]% | 57.5% | 280/359 (78.0%) |
| brooklyn_v1 | spark_v3 | 51 | [42.0, 60.0]% | 56.4% | 272/346 (78.6%) |
| brooklyn_v2 | spark_v2 | 40 | [32.0, 48.0]% | 48.7% | 233/303 (76.9%) |
| brooklyn_v2 | spark_v3 | 33 | [25.0, 41.0]% | 49.2% | 220/298 (73.8%) |
| brooklyn_v3 | spark_v2 | 51 | [42.0, 60.0]% | 51.1% | 259/321 (80.7%) |
| brooklyn_v3 | spark_v3 | 47 | [37.0, 56.0]% | 50.2% | 252/309 (81.6%) |
| brooklyn_v4 | spark_v2 | 51 | [42.0, 60.0]% | 50.6% | 259/317 (81.7%) |
| brooklyn_v4 | spark_v3 | 48 | [39.0, 57.0]% | 50.3% | 254/310 (81.9%) |

## De Belote declaring

| de Belote | Against Brooklyn | Taking | Contracts made | Mean numeric bid | Ordinary mean margin |
| --- | --- | ---: | --- | ---: | ---: |
| spark_v2 | brooklyn_v1 | 42.5% | 217/265 (81.9%) | 102.91 | 19.87 |
| spark_v3 | brooklyn_v1 | 43.6% | 223/267 (83.5%) | 102.81 | 20.57 |
| spark_v2 | brooklyn_v2 | 51.3% | 271/319 (85.0%) | 102.41 | 20.92 |
| spark_v3 | brooklyn_v2 | 50.8% | 263/308 (85.4%) | 102.18 | 22.34 |
| spark_v2 | brooklyn_v3 | 48.9% | 255/307 (83.1%) | 102.15 | 19.37 |
| spark_v3 | brooklyn_v3 | 49.8% | 262/306 (85.6%) | 101.99 | 21.62 |
| spark_v2 | brooklyn_v4 | 49.4% | 256/309 (82.8%) | 102.14 | 19.99 |
| spark_v3 | brooklyn_v4 | 49.7% | 261/306 (85.3%) | 101.86 | 21.78 |

## Both opponents pooled

| Brooklyn | Wins / 200 | Win 95% interval | Taking | Contracts made |
| --- | ---: | --- | ---: | --- |
| brooklyn_v1 | 107 (53.5%) | [46.5, 60.5]% | 57.0% | 552/705 (78.3%) |
| brooklyn_v2 | 73 (36.5%) | [29.5, 43.5]% | 48.9% | 453/601 (75.4%) |
| brooklyn_v3 | 98 (49.0%) | [40.5, 57.5]% | 50.7% | 511/630 (81.1%) |
| brooklyn_v4 | 99 (49.5%) | [41.0, 58.0]% | 50.5% | 513/627 (81.8%) |

## Calibration by mode

Capots remain in success, taking and wins. Ordinary margins alone exclude achieved capots.

| Brooklyn | Mode | Made / taken | Success | Share of all played deals | Mean numeric bid | Ordinary mean margin |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| brooklyn_v1 | SUIT | 442/538 | 82.2% | 43.5% | 102.6 | 19.46 |
| brooklyn_v1 | SANS_ATOUT | 63/101 | 62.4% | 8.2% | 104.75 | -0.5 |
| brooklyn_v1 | TOUT_ATOUT | 47/66 | 71.2% | 5.3% | 100 | 13.32 |
| brooklyn_v2 | SUIT | 285/368 | 77.4% | 30.0% | 98.59 | 19.1 |
| brooklyn_v2 | SANS_ATOUT | 78/121 | 64.5% | 9.9% | 104.05 | 2.11 |
| brooklyn_v2 | TOUT_ATOUT | 90/112 | 80.4% | 9.1% | 105.27 | 16.02 |
| brooklyn_v3 | SUIT | 360/414 | 87.0% | 33.3% | 100.89 | 22.92 |
| brooklyn_v3 | SANS_ATOUT | 88/135 | 65.2% | 10.9% | 103.26 | 4.23 |
| brooklyn_v3 | TOUT_ATOUT | 63/81 | 77.8% | 6.5% | 101.36 | 16.49 |
| brooklyn_v4 | SUIT | 360/409 | 88.0% | 32.9% | 100.95 | 23.88 |
| brooklyn_v4 | SANS_ATOUT | 89/135 | 65.9% | 10.9% | 103.56 | 4.49 |
| brooklyn_v4 | TOUT_ATOUT | 64/83 | 77.1% | 6.7% | 101.69 | 16.06 |

## Protocol and limits

- Source `50e18f9e3a23c7dbf5dfcebb4999c3589037687a`, web engine, target 1000, four workers. Wall-clock elapsed 106176.5s includes session suspension and is not CPU runtime.
- Reproduce: `python -B benchmarks/bots.py --brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3 brooklyn_v4 --pairs 50 --seed 48000 --workers 4 --output results.json`.
- Each seed is replayed with Brooklyn on team 0 and team 1; dealer `seed % 4`; each bot RNG `seed * 17 + seat`. Display sleeps and broadcasts are disabled. The running server is not contacted or restarted.
- Bots receive only their own hand and public information through the normal web-engine API. Post-decision diagnostics inspect hidden hands without passing them to bots.
- Brooklyn can bid suited, SA and TA contracts. De Belote v2/v3 bid suited contracts and use their current common SA/TA card-play fallback when defending those modes; suited simulations are not used for SA/TA. This is current app behaviour.
- Success uses the actual scoring flag, including strict majority. Taking excludes passed-out deals only. Capots are retained in all outcome rates; explicit Capot bids have no numeric margin. Margins use earned trick/dix-de-der/belote points, not awarded contract or coinche bonuses.
- Win intervals use 4,000 percentile bootstrap draws, RNG 20261020, resampling whole seed clusters. Direct matchups cluster both team swaps; pooled results cluster both opponents and both swaps. Deals inside a game are not independent.
- Fresh seeds were not used to tune the policy. The prior 46000–46049 comparison uses different seeds and another revision: differences from it do not isolate the effect of this trump-void deduction. Different auctions/game lengths also change later hands even when seeds match.
- Checked all 800 unique game keys, complete matchups, team swaps and summaries against raw records. No failure or capot was dropped.
- Replayed eight complete games: V1 against both de Belote versions, both team swaps,
  for seeds 46000 and 48000. Every saved deal, outcome and diagnostic was reproduced
  exactly, including the prior seed under V1's unchanged policy.

Data: [raw games](results-2026-10-31-partner-support.json), [pooled summary](summary-2026-10-31-partner-support.json).
