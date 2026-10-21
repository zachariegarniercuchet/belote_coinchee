# Brooklyn v1 — David

Rule-based card play, with Spark's existing bidding policy. No hidden hands,
Monte Carlo search or changes to the existing bots/default bot.

## Playing style

- Both attacking partners draw enemy trumps: jack first, then a master nine
  (or the next master); otherwise lead small. Do not sacrifice the nine under
  an unseen jack. Stop when public card counts/voids prove opponents are out.
- Cash valuable winning cards in attack and defence, rather than automatically
  choosing the cheapest winner. An unknown void is not a guaranteed cut, but
  a known impending cut is a reason not to throw away an ace unnecessarily.
- Feed a reasonably safe winning partner. Discard cheaply when unable to win.
- Exception: when attacking, last to play, with opponents known to have no
  trumps, a cheaper winner may preserve a future ace.
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

## Brooklyn v2 — initial partnership bidding convention

V1 is unchanged. V2 inherits the same card play, but opens with at least
three trumps including J or 9: 80 for one honour, 90 for both, plus belote at
the opening: 10 with three trumps, 20 with at least four. This is the bidding
valuation, not a change to the actual +20 belote score. The supporting partner adds 10 per missing trump
honour held and per non-trump ace. The trump ace is included in the base
80/90 description and never earns another +10. Opener's later credits include
10 per non-trump ace, and 10 for a void with at least
four trumps, or 20 TOTAL for at least two voids with at least four trumps.
Support and bonuses are credited once, not again on each turn. No capot bid.
V1's conservative coinche/surcoinche decisions remain in use.

Credits are relative to the team's last bid, not the intervening opponents'
bid. This avoids turning enemy overcalls into fictitious extra hand strength.
Both attack partners remember public raise amounts via `partner_raises` and
`partner_raise_points`. These survive contract acceptance and reset on the
next deal; history is re-read without spending duplicate credits.

Working parameters following David's clarification (20 October):

- `SECOND_TENS_REQUIRED = 2`: +10 for at least two dix seconds (ten + exactly
  one other card in a non-trump suit). Three side-suit dix seconds cannot fit
  alongside three trumps. This is an initial parameter to measure, not a
  claimed optimal valuation. A non-trump ace is credited separately at +10.
- Initial entry is limited to the 80/90 trump description plus belote, whether
  opening an empty auction or overcalling opponents. Aces, voids and dix
  seconds are reserved for rebidding and cannot fund initial entry. Belote
  already included at the opening is NOT added a second time later.

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
