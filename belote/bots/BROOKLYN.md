# Brooklyn v1 — David

Rule-based card play, with Spark's existing bidding policy. No hidden hands
or Monte Carlo search; the default bot selection is retained.

All players now receive actual public belote/rebelote announcements before
the next card choice. The first locates the unplayed king/queen mate; the
second removes it. Hidden unannounced pairs are never supplied. Brooklyn's
threat assessment uses these owners, and de Belote v2/v3 keep the known card
in that seat in every sampled world, including relaxed samples. Public bonus
information is also retained in their playouts. These shared information
changes are separate from the versioned Brooklyn trump-play rules; older
benchmarks remain attached to their recorded revision.
This includes trump drawing: when the only outstanding trump is partner's
publicly located rebelote, lead a side suit if available. Before the actual
belote announcement its owner remains unknown; an opponent's located mate
is still a trump to draw. The existing card-play journey now verifies the
actual next lead for both announcement orders and all five Brooklyn versions.

## Sans Atout / Tout Atout

All four Brooklyn versions now also consider SA/TA, without replacing their
historical suited bidding/playing policies. This changes the auction space:
older benchmark snapshots do not measure the current six-contract game.
Rules and values follow §11 of the repository's FFB PDF.

- Open with at least two immediate controls, counted as uninterrupted
  sequences from A at SA or J at TA. SA also accepts three suits stopped
  by an ace, at least second ten, or at least third king. Value plausible
  survivors after sacrificing small cards to absent honours: 85% for
  immediate controls, 55% for cards requiring establishment, or 65% for
  protected SA tens / at least third kings. TA adds 20 per belote.
- SA shape penalties: 10 per void, 4 per singleton without an ace, 2 per
  other suit without a stopper. Five immediate controls halve those
  penalties; a master sequence of at least seven waives them when the player
  has the opening lead (public dealer information). A void is not an absolute
  ban: exceptional hands can compensate. These are development parameters,
  fixed before the comparison rather than fitted success probabilities.
- A recoverable value of 30 opens 80, then each further 10 funds another 10.
  These initial thresholds are not calibrated success probabilities.
  SA has no belote and neither mode receives void/cutting credits.
- Support with +10 per immediate control, +20 per TA belote. Spend each
  contribution once, measured from the last team bid, ignoring enemy
  overcalls. Suit/mode switches start a fresh budget. Do not add opener's
  belote again at rebid. Prefer the existing suited choice on equal value.
- SA support also adds +10 per exactly second ten without its ace, and +10
  for every two at least third kings outside the already counted prefix.
  Never count an honour both as an immediate winner and a protected card.
  These support credits describe the partner's hand; they do not repeat
  the opener's own evaluation at a rebid.
- Bid a mode capot only when all eight own cards are immediate controls.
  Do not coinche SA/TA using the old single-trump-suit evaluator.
- On lead, retain short masters. Start a purge with at least three cards
  and the top two remaining cards (initially A/10 at SA, J/9 at TA), or four
  cards and the top remaining card. Retain this intent across losses and
  side-suit re-entries even when the remaining length drops.
- During a purge, lead the highest card if publicly master; otherwise force
  the missing honours with a small card, then resume cashing when master.
  Also continue if both opponents are publicly void in the suit and partner
  may still follow. One enemy void is insufficient. All inference uses
  public plays only. Reset purge intent at every new deal/accepted contract.
- Otherwise establish a suit with waste instead of automatically cashing a
  short SA ace / TA jack. Following-suit play is unchanged: feed a safe
  partner with non-master points; take with a safe winner or the weakest
  current winner when overtaking remains possible. TA still requires climbing.

The [latest full-game comparison](../../benchmarks/2026-11-01-current-bots.md)
at `51c8d48` runs 800 games on fresh seeds 52000–52049, including V4's
held-master protection. V1/V2/V3/V4 win 50.0/33.5/46.5/45.5% overall.
V4 makes 90.7% of suited contracts, 63.1% SA and 72.2% TA; SA remains its
least reliable mode. V4 minus V3 is −1 percentage point in game wins,
seed-cluster 95% interval [−3, +1]; no improvement is established on this lot.
This snapshot predates the clarification limiting attacking master
preservation to last seat when a winning trump is available.

The earlier [frozen-contract card comparison](../../benchmarks/2026-11-01-cardplay.md)
replays V1/V3/V4 on the same 500 distributions and public auctions, after
the shared public-belote information fix and restoration of V4's return to
partner's opening suit. V4 makes 86.47% of the attacking suited reference
contracts versus V1's 83.35%; these are duplicate-deal results, not game wins.
The [earlier fresh direct comparison](../../benchmarks/2026-10-31-partner-support.md)
uses 800 games after the suited support deduction, on seeds 48000–48049.
It reports V4 at 49.5% wins and 65.9% SA success; the earlier favourable
SA sample does not establish that the SA policy is reliable on new deals.
The [SA before/after comparison](../../benchmarks/2026-10-30-sa-bidding.md)
uses 800 games per policy and includes the follow-up purge play in both
policies. The [older 800-game snapshot](../../benchmarks/2026-10-29-sa-ta.md)
predates that purge policy and does not measure its performance.

Other non-random families retain the initial SA/TA master-cashing fallback;
their bidding remains suited. Spark's single-trump simulations are not used
for mode contracts. The follow-up purge policy is Brooklyn-only.

## Playing style

For suited partnership bidding, v2/v3/v4 subtract 10 from the supporter's
total credit when holding no trump in partner's suit, floored at zero.
Apply this once before subtracting credits already spent, and reset it with
the suit episode. Two side aces with no trump therefore support +10, one ace
supports zero; holding even one trump avoids this deduction. Independent
openings, suit changes and SA/TA budgets keep their own evaluations. V1
already requires at least three trumps to support a suited contract.

Latest shared-policy benchmark: [weakest winning trump in attack](../../benchmarks/2026-10-26-trump-control.md),
all three versions rerun at `8f02342`. V1/v2/v3 retain their published playing
policies; the clarification separating strongest trump FOLLOW from cheapest
CUT is now isolated in v4 below, not retrofitted into the old versions.

- Both attacking partners draw enemy trumps: jack first, then a master nine
  (or the next master); otherwise lead small. Do not sacrifice the nine under
  an unseen jack. Stop when public card counts/voids prove opponents are out.
- In v1/v2/v3 attack, take with the weakest sufficient legal trump, whether
  following trump or cutting. V4 changes following only (see below). Legal
  compulsory overtrumps and the safe-partner feeding priority remain.
  V4 also protects held masters when following trump in defence (see below).
- For non-trump winners, before last seat cash the highest-point reasonably safe winner; otherwise
  use the weakest card that currently wins (K before 10 with A unaccounted for).
  In last seat, cash the highest-point non-trump winner, even with enemy trumps gone.
  This applies in attack and defence to all four versions. Safety uses public
  higher-card counts and known cutting threats, not hidden hands: an unknown
  void is not treated as a guaranteed cut. Duck a known impending cut when a
  losing legal alternative avoids wasting a winner.
- Feed a reasonably safe winning partner with points likely to be lost: loose
  tens and unmastered honours, favouring singletons on equal value and cards
  below an ace rather than sacrificing that ace. Preserve masters if a cheap
  discard is available. This shared policy applies to all Brooklyn versions.
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

## Brooklyn v4 — distinguish trump follow from cut

V4 inherits v3's recoverable-card bidding and public partnership support.
Before the first trump lead it may lead its singleton to start drawing.
AFTER a trump round, it keeps its last trump on its own lead when a side suit
is available, EXCEPT to return partner's first-announced suit while opponents
may still hold trump. With no possible enemy trump there is no hunt.
This restores V3's partner-return exception following David's clarification.
Forced following/cutting/overcutting remains legal and required;
the public first-trump marker resets each deal. No late-deal threshold.
When following a trump lead in attack, take the highest-point safe winner in
second or third seat: usually a master, or no possible enemy overtrump on
public information. Without a safe winner, risk only the weakest current
winner. In last seat, keep a held
master by playing the weakest legal winner. Defence retains master
preservation in every seat. If no card wins, spare the next master likewise.
Climbing is mandatory: spend the master if it
is the only legal choice. Publicly fallen honours, including the current
trick, determine the next master (9 after J, etc.). In last seat or defence,
without a held master, take the winner worth the most points. When
cutting/overcutting a side suit in attack, keep the smallest sufficient legal
trump. Do not apply the following rule to leads: lead J first, a master next,
otherwise small (do not sacrifice 9 under an unseen J if a lower trump exists).
Defensive cuts remain unchanged between the Brooklyn versions. Their versioned
trump-play rules remain distinct; shared public-information changes are
documented above. Benchmark results always belong to their recorded revision;
the comparison at `c7be4ff` predates this master-preservation rule.

The possible context-sensitive defensive-cut policy remains deferred in
AGENTS.md, without a reserved version number. V5's partner-specific fixes
below do not implement that general defensive-cut idea.

The existing three journey tests cover all four versions and full seeded
console/web parity. No frontend code changes are needed: the catalogue exposes
v4 through the same lazy factory. No browser verification was performed.
The [400-game comparison](../../benchmarks/2026-10-26-v4.md) at `09e0bf9`
gives v4 49%/43% wins versus de Belote v2/v3, compared with v3's 46%/46%.
V3's rerun exactly matches its previous outcomes and metrics. No clear overall
v4 win improvement is established; v1/v2/v3 runtime modules remain frozen.

## Brooklyn v5 — guarded side ten in defence (3 November 2026)

David's reported hand has Nora holding spade 9, heart 10/J/7, club Q and
diamond K/J/9. After spade 8/Q/A/9, an enemy leads heart K. The historical
policy detects that the heart 10 can be overtaken, but still selects the
weakest current winner. All five Brooklyn versions reproduce that choice
when hearts are not trump. It is not a V5-specific regression.

V5 now ducks with a cheaper legal loser when defending a suited contract,
following a side suit before last seat, with the 10 as the only current
winner and no safe winner. On this deal it plays heart 7, retaining 10/J;
enemy K/A/8 take 15 card points instead of 25. This does not guarantee that
the retained ten will be cashed later. A safe, last-seat or forced ten keeps
its previous behavior. Attack, requested trump, SA/TA and V1–V4 are unchanged.
The existing representative card-play test covers this deal and those limits;
the seeded full-game test still checks legal play and console/web parity.

A small duplicate comparison used `benchmarks.cardplay.common_auction` and
`replay`, seeds 56000–56007, V5 versus de Belote V2/V3, both team swaps,
with identical hands, auction, contract, dealer and RNG. The before class
was loaded from `a7e4135`; only the V5 factory changed for the after replay.
All 32 auctions produced a played deal: 14 spades, 10 clubs, 2 hearts,
2 SA and 4 TA. One deal changed (seed 56002, defence team 1, de Belote V2,
spades): defence earned 42 points including bonuses instead of 15; the
contract remained made. The other 31 deals played identically. This small
development sample does not establish a gain in full-game win rate.

## Brooklyn v5 — suit-switch support and partner priorities

V5 builds on V4's openings, ordinary partnership bidding and card play,
with the partner-specific overrides below.
After a trump round, retain the last trump on an attacking lead when a side
suit is available and at most two enemy trumps remain possible. Partner's
first announcement no longer overrides this control preservation. Count
possible enemy cards from public plays, voids and belote ownership; do not
count located partner cards as enemy targets. First-round drawing and the
existing return with more possible enemy trumps remain. Forced following,
cutting and overcutting, plus SA/TA play, are unchanged. The reported game
`8c41a72bf410469cad63f751b8216de5`, deal 2, now leads the diamond ace at
trick 3, retaining the last spade 9 instead of drawing partner's spades.
V4 still leads the 9 on the identical history. Without the public belote,
three spades remain possible enemy cards and V5 retains its old return.
This is a conservative control rule, not a calibrated strength gain. A
paired replay freezes those hands, auction and first two tricks, then uses
four V5 bots for the continuation, changing only Nora's trump-drawing rule.
Console/web logs match for both policies. The old continuation scores
0–380 (capot), the new one 10–280; retaining control can cost a capot.
This simulation does not reproduce the human players' later choices or
establish a general improvement in win rate.
Support must never describe the same contribution twice, across the whole
public auction. Our earlier suited/SA bids already describe the aces; no
later switch adds ace credit again, including 80 -> 90. Our earlier TA bid
already describes every J/9/belote. Earlier suited bids describe the honours
and belote of those suits. After partner switches to a new suit, only its
previously undescribed J/9 (+10 each) and belote (+20) fund support. Returning
to an already described suit, or switching from our TA to a suit, adds none.
Existing spent credits and the no-trump-in-hand deduction remain. A new
deal resets memory. The reported 90 SA / enemy 100 spades / partner
120 clubs sequence now passes with two side aces and no club J/9/belote,
instead of bidding 140 clubs. An ordinary partner opening at 100 clubs
still allows the same hand to support to 120. Existing nominal journeys
cover both paths, as well as game `22ff8a7fffa344d0a548977f372d174c`, deal 1:
80 hearts / enemy 90 spades / partner 100 clubs now receives 110 clubs
with the club J, instead of a pass. The club ace adds no further credit.
After our suited/SA announcements and partner's switch to TA, support only
J (+10 each) and belotes (+20 each) in still undescribed suits. Nothing in
any previously announced suit adds credit again. Other-suit 9/aces and
longer master sequences add no further credit. Deduct our already spent TA
raises, including after enemy overcalls or partner rebids. A return to our
previous TA adds no support. Switching to SA after our suited bid deducts
the already described aces from ordinary SA support; returning to our SA
adds no support. Without our own announcement in an earlier team episode,
ordinary partner support remains unchanged. Existing auction journeys cover
the reported deal, SA/TA switches, returns to earlier descriptions, spending
credits once and fresh ordinary openings, while preserving V1/V2/V3/V4.
A possible small two-ten support bonus remains a TODO;
its amount and required protection are not yet specified.

The [paired TA-switch comparison](../../benchmarks/2026-11-07-ta-switch.md)
isolates `bd86f1d` from `a640745` on 400 full games, seeds 58000–58049.
Both win 85/200 and make 73/94 TA contracts. Four TA contracts drop from
100 to 90 and remain made. Mean TA bid falls from 101.17 to 100.74; no
win gain is observed. Only two seed clusters have changed records, so the
sample does not establish equivalence or measure play with a human partner.

The [paired before/after comparison](../../benchmarks/2026-11-02-sa-switch.md)
at `42d3661` isolates this SA/TA-to-suit support correction from `6029e7c`,
with identical card play. On 400 games (200 per revision), both win 99/200
and make 504/616 contracts. Four initial bid reductions occur on achieved
capots, with no win or contract-success change. SA remains 60/110 (54.5%)
in both lots. This does not establish equivalence on other deals or measure
the convention with a human partner.

This convention uses only our hand and public auction history. V1/V2/V3/V4,
de Belote and the default bot are not changed. Existing partnership and full
game journeys cover the new version, including console/web parity. The
deferred general defensive cutting policy above is not implemented by V5.

Before last seat, do not voluntarily cut or overcut a currently winning
partner if a legal card keeps partner winning. Do not replace this priority
with a blanket test that partner must hold the highest remaining rank.
Following suit, do not overtake with a merely current winner when no own
master is available (10 over partner's K with A still missing). Forced
following, cuts and overtrumps still come from the legal-card set.

Last defender banks the highest-point vulnerable legal card, including one
that overtakes partner: team ownership is already assured. Keep future
masters/sequences and side aces, except A-10 or a publicly endangered ace in
the last two cards. At least one card must still be played if all are
protected. This overrides only V5, in suited contracts and SA; TA is unchanged.

David's 100-diamond deal was replayed through the web engine with all 32
reported cards and the first trick 7/A/9/8 of spades. On Q/J of spades next,
V4 cuts 9 diamonds and Octave must overtrump J; corrected V5 discards 7 hearts
and keeps its 9, with Octave choosing 10 diamonds. Existing nominal journeys
cover this position, third/last-seat charging, protected masters/aces and
forced cards; full console/web and SA/TA journeys pass. No browser check or
new full-game performance benchmark was performed for these partner fixes.

The [paired 400-game comparison](../../benchmarks/2026-11-02-v5.md) at
`40e343d` uses fresh seeds 54000–54049, V4/V5 against de Belote v2/v3,
with both team swaps. Both versions win 90/200 games; V5 makes 357/401
suited contracts versus V4's 356/401. Only three seeds produce different
recorded trajectories. No win improvement is established, and this does
not measure partnership understanding with a human.
That snapshot predates the partner-specific card-play fixes above and the
SA/TA-to-suit support correction; it does not measure current V5 performance.
That snapshot predates the later fix retaining the last trump even when
partner opened; the new fix has journey checks, not a fresh full benchmark.
Eight short mixed-bot control games also completed; this is an integration
check, not a new win-rate estimate. No browser verification was performed.

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

Card play stays shared except for v3's last-trump preservation: NEVER apply
it before the first trump lead, or when partner was the first team
bidder in the final trump suit. Otherwise, after trump play has started,
v3 may keep its single trump while a side lead is available. A cut alone
does not count as a round of trump drawing. No late-deal
threshold. The first bidder is read from public auction history at contract
acceptance and reset each deal; unknown history does not block a first trump
lead. Forced plays remain legal. The old blanket singleton rule was too broad.
The [first-trump benchmark](../../benchmarks/2026-10-26-first-trump.md)
at `feb956d` measures this correction: 46% wins against both de Belote v2/v3,
39.6%/39.5% taking and 85.4%/84.5% contract success. No clear before/after
win gain on this sample. Older v3 measurements below retain their revisions.
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
