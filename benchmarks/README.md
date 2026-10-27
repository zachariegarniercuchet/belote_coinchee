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

## Saved comparisons

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
