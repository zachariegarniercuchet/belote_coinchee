# Bot simulation benchmark

From the repository root, with the web dependencies installed:

```powershell
.\.venv\Scripts\python.exe -B benchmarks/bots.py --pairs 50 --workers 4 --output results.json
```

This runs 100 full games per matchup (400 total): Brooklyn v1/v2 against
de Belote v2/v3, target 1000, seeds 30000–30049, each with Brooklyn on both
teams. Change `--seed`, `--pairs` or `--target` for a separate sample.
The command does not contact the running server, create live rooms, or alter
bot policies. Web-engine display sleeps and broadcasts are disabled.
To run the hybrid alone, add `--brooklyn brooklyn_v3` (200 games at 50 pairs).
To include it alongside both baselines, use
`--brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3` (600 games). The legacy
`changes` field still compares v2 minus v1 only when both are present;
all selected versions have full metric rows and per-game records.
Use `--brooklyn brooklyn_v3 brooklyn_v4` for a 400-game paired comparison of
the new v4 with its unchanged v3 control. V5 is a deferred idea, not a bot.
Progress is printed to stderr; the summary goes to stdout. Optional JSON
output also contains every game's deal outcomes and lead counts, plus the
source revision, so reported metrics can be audited.

After adding SA/TA, rerun all versions with
`--brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3 brooklyn_v4` (800 games).
Deal records include `contract_suit`, `capot_bid`, belote points and the
opener's number of belote pairs. Summary `by_mode` separates suited contracts,
SA and TA (counts, take share, success, numeric mean bid and margins).
SA/TA have no single trump-suit count: their opening diagnostics are null,
and they are excluded from suited J/9 opening and trump-hunting diagnostics,
but included in every overall outcome/calibration metric.
Historical snapshots remain tied to their revision; comparing before/after
does not isolate the effect of SA/TA from other intervening changes.

Metrics:

- Taking share excludes passed-out deals; contract success is the actual
  scoring-engine flag, including its majority condition.
- Bid margin is earned trick points + dix de der + belote, minus the numeric
  bid. It excludes awarded contract/coinche bonuses. Calibration is reported
  both with and without capot deals; failed contracts are never omitted.
  **Capots are included in game wins, taking, contract success and scores.**
  Only the separate `margin_no_capot` view excludes capot deals, since their
  special dix-de-der bonus inflates the ordinary bid cushion. `margin_all`
  retains capots achieved under numeric contracts. An explicit Capot bid has
  no numeric bid to subtract, but still counts in every outcome rate.
- Opening diagnostics describe the original opener's trump count and J/9
  holding in its team's final suit episode, not necessarily the final bidder.
- Trump-drawing opportunities are actual attacking lead decisions with both
  a legal trump and a legal side-suit card, while an opponent actually holds
  trump. Claims and automatic last tricks are excluded because bots did not
  choose those leads. Hidden hands are inspected only AFTER the decision and
  never passed to a bot. Side-ace and jack-leading rates use the same sample
  (jack rate additionally requires a trump jack in hand).

The 95% percentile-bootstrap win intervals resample whole seed pairs (4,000
draws, fixed bootstrap seed), not correlated games/deals as independent trials.
The v2-minus-v1 win difference also preserves seed matching. Intervals require
at least two seed pairs; very small runs are smoke checks, not evidence for a
ranking. No normality assumption or hypothesis-test p-value is used.

This is a descriptive development benchmark. Reused seeds are not a holdout.
Different bidding policies change subsequent deals/game lengths; matched seeds
do not guarantee identical hands throughout games. Trump-leading rates depend
on the contracts won and are NOT causal measurements of that strategy's value.
Do not tune on results and present the same sample as independent validation.

## Card play at the same contract

```powershell
.\.venv\Scripts\python.exe -B benchmarks/cardplay.py --seeds 500 --seed 50000 --control-seeds 50 --workers 4 --output cardplay.json
```

This compares duplicate single deals, not complete games to a target score.
For each seed, generate the same deck/dealer and use Brooklyn v1 and v4 as
two reference bidding policies against de Belote v2/v3, on both teams.
Those eight reference conditions are chosen before the compared card play.
Force the whole legal public auction, including bidder, suit, level and
coinche, and replay each attacking suited condition with Brooklyn v1, v3
and v4. V2 has exactly V1's card-play methods and is not duplicated.

Every bot still observes the ordinary bidding calls with its own hand and
the frozen public history. Proposed bids are ignored; normal contract,
trick and public belote notifications are delivered by the web engine.
Assertions verify equal initial hands, auction, contract and opening lead.
No hidden hand is passed to an opponent or candidate bot.

On the first 50 seeds, also replay defensive, SA and TA conditions.
Only SA/TA policies are shared and their complete plays/scores must match
exactly. V4's suited defence now preserves held trump masters, so defensive
samples can differ. Passed-out auctions and unplayed sample conditions remain
listed in the raw population. All capots and coinches are retained.

Results report earned card/bonus points, awarded score differences and
contracts made/saved/lost at the same contract. They are not full-game win
rates. Keep both reference-auction strata visible; pool only with explicit
weights. Uncertainty must cluster whole seeds, including both references,
opponents and team swaps. Identical frozen histories under the two reference
policies reuse their exact seeded replay; records mark that reuse and are
not treated as independent observations.
Full traces remain in standard JSON, with one compact line per reference
condition to keep result artifacts small without removing data.

## Saved comparisons

- [Current Brooklyn vs de Belote](2026-11-01-current-bots.md): 800 complete
  games on fresh seeds 52000–52049 at `51c8d48`, including public belote
  information, partner-return leads and V4's held-master protection on
  requested trump. All four versions, both opponents and per-mode calibration.
- [Card play with frozen contracts](2026-11-01-cardplay.md): 500 distributions,
  1,574 attacking suited reference conditions, v1/v3/v4 replays and 230
  identical defense/SA/TA controls at `c7be4ff`. Includes the public belote
  information fix and restored V4 return to partner's opening suit.
- [Fresh Brooklyn vs de Belote comparison](2026-10-31-partner-support.md):
  800 games on seeds 48000–48049 at `50e18f9`, after the no-trump suited
  support deduction, with direct opponent results and per-mode calibration.
- [SA distribution and protected honours](2026-10-30-sa-bidding.md): paired
  800-game before/after runs (1,600 total), fresh seeds 46000–46049, all four
  Brooklyn versions, SA selection/support changes and unchanged TA evaluation.
- [SA/TA across Brooklyn v1–v4](2026-10-29-sa-ta.md): 800 games at
  `dc31e65`, with per-mode success/calibration and all capots included.
- [Versioned Brooklyn v4](2026-10-26-v4.md): 400 games at `09e0bf9`, newly
  rerunning v3 as an unchanged control; defensive v5 remains deferred.
- [V3 first trump lead and return to partner](2026-10-26-first-trump.md):
  v3 at `feb956d`, 200 games; v1/v2 remain unchanged saved baselines.
- [Weakest winning trump in attack](2026-10-26-trump-control.md): all three
  Brooklyn versions rerun at `8f02342`, plus the supplied 80-heart deal replay.
- [Brooklyn v3 recoverable cards](2026-10-21-recoverable.md): revised evaluator
  and last-trump preservation at `75720f0`, 200 games and saved paired baselines.
- [Brooklyn v3 hybrid](2026-10-20-hybrid.md): v3 at `7b3c7d2` versus both
  de Belote opponents, paired with unchanged saved v1/v2 baselines.
- [After risk-aware winning-card selection](2026-10-20-risk-aware-winners.md):
  both Brooklyn versions rerun at `7fc077f`, with paired before/after results.
- [After the shared ace-preservation fix](2026-10-20-ace-preservation.md):
  both Brooklyn versions rerun at `1fea8bb`, including capots in outcome rates.
- [Qualified openings and suit switches](2026-10-20-qualified-openings.md):
  bidding amendment at `865e23a`, before the shared card-play fix.
- [Previous v2 policy](2026-10-20-current.md): frozen at `edbd52e`, retained
  for comparison rather than overwritten with later measurements.
