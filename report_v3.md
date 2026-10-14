# Report — SparkBot v3 (beats v1, v2 and HeuristicBot)

## 1. Setup & verdict

- `belote/spark_bot_v1.py` — v1, frozen backup (unchanged).
- `belote/spark_bot_v2.py` — v2, search bot (unchanged).
- `belote/spark_bot_v3.py` — NEW `SparkBotV3` (subclass of v2).
- Web app (`game_session.py`) and console (`cli.py`) now play **v3** by default.
  All four (`SparkBot`, `SparkBotV1/2/3`) are exported from `belote`.
- **Verdict: v3 > v2 > v1 > HeuristicBot**, each link validated by same-seed
  seat-swapped matches (identical deals, seats exchanged — deal luck cancels
  exactly since the bots are deterministic):

| Matchup | Matches | Wins | Net pts/match |
|---|---|---|---|
| v3 vs v2 (8 seeds) | 1600 × 8 donnes | **826 – 763**, 7/8 seeds positive | +44 |
| v3 vs v1 (2 seeds) | 400 × 8 donnes | **222 – 177** | +88 |
| v3 vs HeuristicBot | 200 × 8 donnes | **176 – 24 (88 %)** | +615 |

Honesty note: v3-vs-v2 is small (+44/match ≈ +5.5/donne) but consistent —
significant by sign test over seeds (7/8, p ≈ 3.5 %). v2's jump over v1
(+75) remains the big step; v3 is a solid refinement, not a revolution.

## 2. "Does the bot take too much risk when it bids?" — bidding audit

600 donnes, per-level success / mean margin (raw − bid) / EV differential:

| Level | Success | Margin raw−bid | EV when made | EV when chuted |
|---|---|---|---|---|
| 90 | 76–84 % | +18 / +23 | +162 / +166 | −261 / −267 |
| 100 | 74–75 % | +17 | +192 / +200 | −260 / −306 |
| 110 | 77–89 % | +19 / +20 | +218 / +233 | −269 / −270 |
| 120 | 71–84 % | +17 / +22 | +262 / +269 | −282 / −285 |

Answer: **no, it is not too risky**. Mean margin is +17 to +23 at every level
(a full trick of cushion), chute rate 11–29 %, and every level is strongly
+EV (breakeven would be ~65–70 % success). Notably v2's *play* lifts the same
bids: v2-team 90s make 84 % vs v1-team 76 %, 110s 89 % vs 77 %. Bidding was
therefore left UNCHANGED in v3 — the audit says it is near-optimal.

## 3. "Knowing all the cards, could the bot have done better?" — double-dummy audit

I wrote an exact minimax solver (alpha-beta + transposition table, real
scoring) and audited 202 non-forced decisions in tricks 6–8 of real v1 donnes:
16 "errors" (8 %) at 142 pts average cost. Two worst cases, worked by hand:

**Example A — donne 13, trick 7.** Contract 110 Pique by opponents. Partner
leads... partner already won the trick with trump 9 (unbeatable — everyone
else has played). Bot held 10 + 7 of Diamonds and played the 7; optimal banks
the master-10 (+400 swing: the 10 avoids being cut next trick AND flips the
contract to a chute). **Guessable with certainty? YES** — bot played last, so
the trick was secured in every possible world. A "feed masters when secured"
rule was built and A/B-tested: **result ≈ 0** (600–593). Why: the rule fires
0.64×/donne but jackpot spots are ~100× rarer; feeding master-aces that would
win later offsets the gains. Dropped — a good lesson that double-dummy
"errors" overstate what is achievable under uncertainty.

**Example B — donne 20, trick 7.** Contract 110 Clubs by opponents' declarer
leads Valet-Coeur; bot held Ace + 8 of Coeur. Bot took with the Ace (−150);
double-dummy ducks the 8 (+250, contract chutes). **Guessable? NO — and the
bot was RIGHT.** Full EV analysis: the opponents' last card is the outstanding
Coeur boss with probability ~1/3 (one of 3 unknown slots). Duck wins big iff
it is (chute), but gifts the Ace (11 pts + lead + dix-de-der) otherwise; take
does the exact opposite. The two lines are mirror images (±460): at 1/3 the
take is the correct belief-action. v2 AND v3 both take — verified. This is the
report's key insight: **optimal-under-uncertainty ≠ double-dummy-optimal**,
and chasing perfect-info play can be wrong.

**Consequence for v3:** no hand-written endgame rules (all washed out in A/B:
blind chasse −90, void-aware leads 0, secured-feed 0, take/duck sweeps 0).
The fix is better *search*, which averages correctly over beliefs.

## 4. v3 = v2 + exact endgame + auction-aware worlds + more worlds

1. **Exact endgame per world.** When ≤ 3 tricks remain, each sampled world is
   solved with exact minimax (shared transposition table per decision)
   instead of heuristic playouts. Early donne keeps fast heuristic playouts.
2. **Auction-aware world sampling.** Bids constrain hands — proven floors:
   any 90+ opener holds 2+ trumps in the suit (a 1-trump hand mathematically
   cannot reach the opening threshold, for ANY bot in this repo); a support
   raise or a coinche means 3+ (only the v1-family ever raises/coinches, and
   all require 3+). Enforced with graceful fallback (voids-only, then free).
3. **More worlds**: 12 early / 6 late-exact (exact values are precise, so late
   needs fewer worlds). Cost ≈ 240 ms/donne with 2 search seats — fine live
   (bots already "think" ~1 s) and fast enough to validate by simulation.

Position checks: v3's search now values both example spots correctly *under
its beliefs* (takes Example B — proven right above; Example A remains a rare
jackpot the rule-based fix couldn't capture either).

## 5. Methodology notes (traps caught)

- Single-seed "wins" of +80 turned out to be deal luck (pure v1-vs-v1 control
  reproduced them exactly). All headline numbers use same-seed seat swaps.
- Branch-fire counters killed two phantom improvements (constant tweaks and
  last-trick logic that fired ~0× in thousands of donnes — the last trick is
  always forced since everyone holds 1 card).
- v3's K-sensitivity was checked on Example B (K = 6/12/24 all take — correct,
  since P ≈ 1/3 < 1/2 regardless of sample size).

## 6. Use

```python
from belote import Game, SparkBotV3, SparkBotV2, SparkBotV1, HeuristicBot
players = {0: SparkBotV3(0), 1: SparkBotV2(1), 2: SparkBotV3(2), 3: SparkBotV1(3)}
Game(players, target_score=1000).play_until_end()
```

## 7. Limits / next steps

- v3-vs-v2 is real but small; the next big jump likely needs opponent-specific
  exploitation or full-game planning (entries, suit establishment order),
  not more search depth.
- Belief model ignores card-reading from *how* opponents play (e.g. leading
  low from boss-doubleton); worlds are uniform given voids/sizes/auction.
- Pre-existing `tests/test_rules.py` failures (2 coinche-scoring expectations)
  are untouched and unrelated (fail on unmodified code too).
