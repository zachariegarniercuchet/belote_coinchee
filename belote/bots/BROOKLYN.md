# Brooklyn v1 — David

Rule-based card play, with Spark's existing bidding policy. No hidden hands,
Monte Carlo search or changes to the existing bots/default bot.

## Playing style

Latest shared-policy benchmark: [weakest winning trump in attack](../../benchmarks/2026-10-26-trump-control.md),
all three versions rerun at `8f02342`. Earlier measurements retain their frozen
revisions and do not measure this correction.

- Both attacking partners draw enemy trumps: jack first, then a master nine
  (or the next master); otherwise lead small. Do not sacrifice the nine under
  an unseen jack. Stop when public card counts/voids prove opponents are out.
- When attacking, take with the weakest legal winning trump in every seat,
  including last: R before J if R suffices, preserving J to control the next
  trick. This covers both following trumps and cutting a side suit. Legal
  compulsory overtrumps still apply; feeding a safe winning partner remains
  higher priority. Defence keeps the previous point-first winner policy.
- For non-trump winners, before last seat cash the highest-point reasonably safe winner; otherwise
  use the weakest card that currently wins (K before 10 with A unaccounted for).
  In last seat, cash the highest-point non-trump winner, even with enemy trumps gone.
  This applies in attack and defence to all three versions. Safety uses public
  higher-card counts and known cutting threats, not hidden hands: an unknown
  void is not treated as a guaranteed cut. Duck a known impending cut when a
  losing legal alternative avoids wasting a winner.
- Feed a reasonably safe winning partner with points likely to be lost: loose
  tens and unmastered honours, favouring singletons on equal value and cards
  below an ace rather than sacrificing that ace. Preserve masters if a cheap
  discard is available. This shared policy applies to both Brooklyn versions.
- Keep side aces when feeding, except with A–10 in hand, or with at most two
  cards left and a publicly known enemy void in the ace's suit plus possible
  enemy trumps. Being late alone is not enough. Legal forced/all-ace hands
  remain playable; an endangered ace is donated only onto a safe partner.
  Discard cheaply when unable to win.
- Following a side suit does not prove a lack of trumps; neither does a
  discard on a winning partner or a refusal to make an impossible overcut.

Names: Miles, Nora, Eli, Maya Brooklyn. Author: David. Portraits not yet set.
The indicative three-star level is not a measured ranking.

## Initial comparisons — 20 October 2026

No parameters were tuned after seeing these results. These are initial
measurements, not a claim of optimal play.

Full games used the actual bidding policies, target 1,000, seeds 30000–30049,
dealer `seed % 4`, deterministic per-seat RNG `seed * 17 + seat`. Each seed
was replayed with Brooklyn taking each team: 100 games per opponent.

| Opponent | Brooklyn game wins | Deals, including passed-out deals |
| --- | ---: | ---: |
| Bohème (`heuristic`) | 84 / 100 | 597 |
| de Belote v1 (`spark_v1`) | 45 / 100 | 652 |

To isolate card play, a separate paired-deal comparison used identical hands,
dealer and bidding history, selected by four Spark bots. Replace one team
with Brooklyn, then swap teams. The reference is the SAME team/hands played
by the opponent's bot in an all-opponent-bot game with that fixed contract.
Metric: change in raw trick points (excluding belote and dix de der).

| Reference bot | Brooklyn attack gain | Brooklyn defence gain | Brooklyn deal replays |
| --- | ---: | ---: | ---: |
| Bohème | +7.06 | +7.58 | 550 |
| Spark / de Belote v1 | +0.16 | +2.08 | 550 per bot |
| de Belote v2 | −4.17 | +6.75 | 24 |
| de Belote v3 | −8.17 | +5.67 | 24 |

The first two rows used independent seeds 10000–10299; 25 passed-out seeds
were omitted. An earlier exploratory run used 0–299, omitting 35 passed-out
seeds. Spark and v1 produced identical results on those samples; they are not
independent evidence. V2/v3 used their default simulation/exact-endgame
settings, seeded per seat, on the first 12 non-passed-out seeds from 20000:
20000, 20001, 20003–20010, 20013, 20015. Those samples are too small for a
ranking. Brooklyn improves over Bohème but is not yet a demonstrated upgrade
over Spark; attacking play against the simulation bots needs investigation.

## Important integration finding

Before the fix, the console engine called `notify_contract` and
`notify_trick_result`, but the web engine called neither. Instrumented seed 0, identical hands/contract:
console = 4 contract notifications and 32 trick notifications; web = 0 and 0.
All four web Brooklyn bots therefore remained `is_preneur=False`.

The web engine now delivers the same contract and all eight trick results,
including claims and automatic last tricks. All players have `contract` and
derived `is_attacking`/`is_defending` properties in the base `Player` API.
`notify_donne_start` clears the old contract before bidding, including deals
where everyone passes; provisional bids are available through `BiddingState`.
Overrides of `notify_contract` must retain `self.contract` or call `super()`.

The existing complete-game test now compares seeded Brooklyn console and web
games, including notification counts, role resets, histories, scores and
winners. The public catalogue journey also checks this common interface on
every bot family. No additional test functions were added for the wiring fix.
Additional mixed-team replays compare Brooklyn against Bohème and Spark v1,
v2, v3 on identical hands and bot RNG seeds: 32, 32, 8 and 8 deal pairs
respectively, all 80 logs identical (including 17 claims and 8 passed-out
deals). Existing bot strategies and the
default selection were not modified; they now receive their missing inputs.

## Brooklyn v3 — hybrid bidding

V3 now uses recoverable-card estimates rather than v1's face-point/strength
bonuses. For each absent higher card, sacrifice the weakest available lower
card before valuing survivors: side 10/K/Q retains 10/K, while K/Q retains
nothing. Credit survivors' actual face points, discounted for trump control;
established side winners additionally get a 0.7 entry factor, but an already
master ace is not discounted merely because a lower card is lost.

Trump confidence: 0.95 with J+9, 0.85 with J, 0.75 with 9, 0.55 with neither.
Side confidence: 0.90 with J+9, 0.85 with J and four-plus trumps, 0.80 with J,
0.75 with 9, 0.65 with neither. Own belote adds 20 once. Voids add only 3 per
possible cut, limited to spare trumps after reserving max(3, 8 - trump count)
for drawing, and only with J. Three/four-trump voids therefore add nothing.
These are explicit initial heuristics, not guaranteed points or fitted odds.

At least three trumps are needed; exactly three require J or 9. Initial frozen
thresholds 30/40/50/60/70 map to 80/90/100/110/120. These use a NEW score scale:
retained own-card points are not the team's eventual trick score. No hidden
hands enter the estimate. V2's legal-candidate/suit-switch machinery remains.

The partner supports the team's suit with +10 for EACH trump J/9 held,
+10 per side ace (never the trump ace), and +20 for trump K+Q, even with only
two trumps. Both J and 9 can count because a v1-valued opening need not hold
either. Contributions are spent once, measured from the last TEAM bid, not
an enemy overcall. Old-suit support does not transfer across suit switches.

The opener's own aces and belote already affect its recovery estimate. V3
does not add v2's entry/rebid bonuses on top, avoiding double counting; its
later ceiling is its own original valuation plus public partner raises.
Belote counts as +20 for either opener or partner, never twice for one hand.
Numeric bids only, no Capot; coinche/surcoinche keep their old independent
Spark evaluator and thresholds. V1/v2 policies and the default bot stay
unchanged. Author David; same Brooklyn names and no portraits yet.

Card play stays shared except that v3 no longer hunts with its last trump
while a side-suit lead is available (forced trump plays remain legal).
The [original hybrid benchmark](../../benchmarks/2026-10-20-hybrid.md) predates
both this evaluator and last-trump change; its 42% win rates do not measure
the new policy. The [recoverable-card benchmark](../../benchmarks/2026-10-21-recoverable.md)
at `75720f0` gives 46%/42% wins, 39.7%/39.2% taking and 85.2%/83.9% contract
success against de Belote v2/v3: safer but more selective, not a demonstrated
overall win improvement. Representative auctions and seeded console/web parity are
checked in the existing three test functions. Run with `--brooklyn brooklyn_v3`.

## Brooklyn v2 — partnership bidding convention

V1 is unchanged; V2 inherits its exact card play. Every initial entry or
new-suit proposal needs at least three trumps including J or 9 AND either
at least one non-trump ace or at least two dix seconds.

- Base 80 for one J/9, 90 for both. The first side ace is INCLUDED in this
  base; every extra side ace adds 10 immediately. Thus one honour + one ace
  opens 80, one honour + two aces opens 90, both honours + one ace opens 90,
  and both honours + two aces opens 100 before belote.
- Belote adds 10 with three trumps, 20 with at least four, on initial entry
  AND overcalling. The actual scoring bonus remains +20.
- Supporting partner adds 10 per missing trump J/9 held and per non-trump ace
  (the first-ace inclusion applies to the opener, not to partner support).
- Trump ace earns no separate credit. Opener's later shape credits are 10 for
  one void with at least four trumps, or 20 TOTAL for at least two voids, plus
  10 for two dix seconds. Aces/belote already spent on entry cannot be added
  again on rebidding. No capot bid; v1's cautious doubles remain in use.

A different suit can be proposed if independently eligible and valuable
enough for a higher legal bid. Select the highest justified legal amount,
preferring support of the current suit on ties. An alternative suit starts a
fresh budget: do not transfer old-suit partner raises or spent credits into
it. Public partner-raise memory resets to the new suit's episode.

Credits are relative to the team's last bid, not the intervening opponents'
bid. This avoids turning enemy overcalls into fictitious extra hand strength.
Both attack partners remember public raise amounts via `partner_raises` and
`partner_raise_points`. These survive contract acceptance and reset on the
next deal; history is re-read without spending duplicate credits.

Working parameters following David's clarification (20 October):

- `SECOND_TENS_REQUIRED = 2`: +10 for at least two dix seconds (ten + exactly
  one other card in a non-trump suit). Three side-suit dix seconds cannot fit
  alongside three trumps. This is an initial parameter to measure, not a
  claimed optimal valuation. The two dix seconds may qualify initial entry
  without an ace, but their extra +10 valuation remains reserved for rebidding.
- Side aces (beyond the included first) and belote fund initial overcalls;
  void/tens credits remain reserved for rebidding. The previous stricter
  entry rule and suit lock were removed following David's clarification.

TODO: use partnership raises to inform leading a new side suit during play.
Amounts alone do not identify specific aces; opener's raises can also contain
belote and shape credits. Do not inspect partner's hand or implement that
card-play inference before its convention is specified.

### Calibration measurements to report when comparing v2

Use fixed seed schedules and swap teams; compare v1 and v2 against the same
opponents. Report game wins, declaring share among non-cancelled deals, and
actual contract success (including the engine's majority condition). Report
failures and their awarded-score cost, rather than success rate alone.

For every numeric contract, measure `result.total_points[team] - bid`, using
trick points + dix de der + belote, NOT awarded contract/coinche bonuses.
Report mean/median and margin buckets below 0, 0–9, 10–20 and above 20, plus
breakdowns by bid amount. Include failures, not just made contracts. Separate
capots, whose special scoring otherwise distorts the margin distribution.
David's tentative goal is a high declaring rate and high success rate, often
bidding 10–20 below the points actually earned. Measure first; tune later.

### First v2 comparison — 20 October 2026

For the latest available benchmark, including the shared ace-feeding fix,
risk-aware winning-card selection and removal of last-seat economy, see
[the risk-aware winner benchmark](../../benchmarks/2026-10-20-risk-aware-winners.md).
The older prototype's measurements below are retained for comparison only.

Policy frozen before running: `a01a62b`. Corrected web engine (`GameSession` /
`NetworkGame`), with display sleeps and broadcasts disabled, not the running
server. Target 1000; seeds 30000–30049, each replayed with Brooklyn on team 0
and team 1; dealer `seed % 4`; each bot RNG seeded with `seed * 17 + seat`.
100 full games per row, 400 total. V1 and v2 use the same card-play policy.
Matched seeds do not imply identical later deals: different bids can change
the number of deals and random draws before the target score is reached.
No parameters were tuned after observing these results.
These historical results PRECEDE David's corrections excluding the trump ace,
reducing three-trump belote to +10, and requiring four trumps for void credit;
they do not measure the corrected policy.

| Brooklyn | Opponent | Game wins | Takes / played deals | Contracts made | Mean bid |
| --- | --- | ---: | ---: | ---: | ---: |
| v1 | de Belote v2 | 53/100 | 306/604 (50.7%) | 240/306 (78.4%) | 102.4 |
| v2 | de Belote v2 | 22/100 | 311/583 (53.3%) | 155/311 (49.8%) | 111.2 |
| v1 | de Belote v3 | 50/100 | 313/622 (50.3%) | 242/313 (77.3%) | 102.5 |
| v2 | de Belote v3 | 18/100 | 308/579 (53.2%) | 152/308 (49.4%) | 111.2 |

Taking excludes passed-out deals: respectively 51, 17, 51 and 14 cancelled
deals in the row order above. Success includes all contracts and uses the
engine's actual success flag, not just a nonnegative point margin.

Calibration below excludes capot deals (either team), but includes failed
contracts. Margin = points earned including belote/dix de der, minus bid;
no awarded contract or coinche bonus. Percentages use the sample in column N.

| Brooklyn / opponent | N | Mean margin | Median | Below bid | 0–9 above | 10–20 above | >20 above |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 / de Belote v2 | 286 | +17.4 | +17 | 23.1% | 12.6% | 19.6% | 44.8% |
| v2 / de Belote v2 | 292 | −2.5 | −2.5 | 53.1% | 15.1% | 14.7% | 17.1% |
| v1 / de Belote v3 | 289 | +15.6 | +16 | 24.6% | 15.6% | 18.0% | 41.9% |
| v2 / de Belote v3 | 288 | −3.4 | −3 | 54.2% | 14.9% | 12.5% | 18.4% |

Including capots, mean/median margins are respectively +26.1/+20,
+5.6/0, +25.7/+19, +5.3/−1 in the main table's row order. Capot counts
on Brooklyn's contracts are 20, 19, 24 and 20. One v2 contract against
de Belote v2 failed despite a nonnegative margin because of the majority
condition. On failed contracts, mean opponent-minus-Brooklyn awarded scores
are 272.3, 280.1, 270.4 and 278.7 points respectively.

V2 contracts made by amount, including capots (made/attempted):

| Bid | Against de Belote v2 | Against de Belote v3 |
| --- | ---: | ---: |
| 80 | 10/23 | 14/23 |
| 90 | 10/19 | 11/20 |
| 100 | 21/55 | 19/53 |
| 110 | 39/88 | 33/86 |
| 120 | 40/74 | 41/75 |
| 130 | 23/37 | 22/36 |
| 140 | 8/10 | 8/10 |
| 150 | 3/4 | 3/4 |
| 160 | 1/1 | 1/1 |

Conclusion for this sample: a small gain in taking rate does not compensate
for the large fall in contract success. V2 bids about nine points higher on
average while ordinary-deal margins are negative. Even contracts left at
80/90 are not reliably made, so excessive rebid bonuses alone do not explain
all failures. Isolating opening quality versus bonus valuation requires a
separate controlled comparison; this run does not establish their individual
causal contributions. Do not promote v2 as an improvement or change the
default bot on the basis of this experiment.
