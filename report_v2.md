# Report — SparkBot v2 vs v1

## 1. Setup

- `belote/spark_bot_v1.py` — frozen copy of the v1 bot (`SparkBotV1`), untouched,
  kept as backup and as the sparring partner.
- `belote/spark_bot_v2.py` — the new `SparkBotV2` (v1 subclass).
- `belote/spark_bot.py` — still the v1 implementation (`SparkBot`), for
  compatibility; the web app (`game_session.py`) and console (`cli.py`) now
  play **v2** by default. `SparkBot`, `SparkBotV1`, `SparkBotV2` are all
  exported from `belote`.

## 2. Bid or play? And what about "prendre les atouts"?

Direct answer from the experiments:

- **The headroom is in card play, not bidding.** In v1-vs-v1 mirrors both
  teams bid identically, so bidding tweaks can only transfer points, not
  create them — and v1's bid levels were already calibrated (every level
  80 %+ success). All remaining edge is in the 32 card decisions per donne.
- **Naive "prendre les atouts" (chasse without the top trump) LOSES.**
  Forcing the declarer to draw low trumps without holding the best remaining
  one cost ~90 pts/match. Mechanism: when trump is led, everyone (including
  your partner) must rise if possible — so leading a small trump burns your
  partner's honours and hands the opponents a cheap trick. Your intuition is
  right that trumps must come out, but only the *holding-top* draws are
  profitable; v1 already does those.
- A **conditional** chasse (draw low only when partner is known void in
  trump, so nothing is wasted) is mildly positive (~+44/match in screening).

## 3. Methodology (and two traps I caught)

1. **A/B every idea against v1**, ideas as `SparkBotV1` subclasses.
2. **Trap 1 — single-seed luck.** First screenings on one seed showed every
   variant winning ~+80. A pure v1-vs-v1 control on the same seed showed the
   identical +80: it was the deal sequence, not the idea.
3. **Trap 2 — variants that never fire.** I added branch-fire counters: two
   "promising" ideas (take/duck constant sweeps, last-trick feed logic) fired
   ~0 times in thousands of donnes — the last trick is always forced (1 card
   each), so there is literally no decision there. Only ideas that fire can
   win; every claim below is backed by fire counts.
4. Final validation uses **same-seed seat swapping**: identical deals with
   seats exchanged (possible because the bots are deterministic), so deal luck
   cancels exactly. 800 matches × 8 donnes for the headline result.

Ideas tested and rejected (mirrored, ~0): blind chasse high/low,
void-aware leads, partner-suit leads, take/duck threshold sweeps,
support/overbid discipline changes in mirror.

## 4. v2: PIMC-lite search on top of v1

Since heuristic rules were exhausted, v2 keeps v1's bidding and v1's heuristic
as the *playout policy*, but decides each card by search:

1. Shortlist: v1's pick + up to 3 alternatives (max 4 candidates).
2. Sample 6 worlds consistent with played cards, current hand sizes and all
   inferred voids.
3. Play out each world to the end with fast v1 policies (shadows re-primed
   from the real trick history).
4. Score with the **real** `compute_donne_score`: exact trick points so far +
   simulated rest, dix-de-der, capot, own belote (known from own initial
   hand), contract bonus/chute. Maximand = score differential.
5. Play the best-mean card (ties → v1's pick).

Cost: ~120 ms/donne with 2 search seats (~0.3 s/donne with 4) — fine for live
web play (bots already "think" ~1 s) and fast enough to validate by simulation.

## 5. Results

v2 vs v1, same-seed seat swap, 8 donnes/match:

| Seeds | Matches | v2 wins – v1 wins | Net pts/match (v2–v1) |
|---|---|---|---|
| 6000 | 200 | 101 – 96 | +62 |
| 6001 | 200 | 116 – 82 | +114 |
| 6002 | 200 | 102 – 96 | +56 |
| 6003 | 200 | 108 – 90 | +71 |
| **Total** | **800** | **427 – 364** | **+76** |

All 4 seeds positive. Excluding 9 tied matches: z ≈ 2.2σ (p ≈ 1 %).
Non-regression: v2 vs HeuristicBot = 50–10 per 60×8 (same ~85 % tier as v1),
4×v2 table stable over 12 donnes.

## 6. How to use

```python
from belote import Game, SparkBotV2, SparkBotV1
players = {0: SparkBotV2(0), 1: SparkBotV1(1), 2: SparkBotV2(2), 3: SparkBotV1(3)}
Game(players, target_score=1000).play_until_end()
```

## 7. Next steps

- More worlds / smarter shortlist (diminishing returns vs speed; profile first).
- Belief model using the auction (partner's/opponents' bids constrain worlds).
- Endgame exact solver for the last 2–3 tricks on top of the search.
- Re-calibrate bid thresholds on v2-vs-v2 logs (play strength shifted slightly).
