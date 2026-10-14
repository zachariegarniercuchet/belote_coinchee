# Report — Muse Spark player (`belote/spark_bot.py`)

## 1. Goal

Build a bot that plays **Belote Coinchée** through the existing `Player` interface
(`choose_bid` / `choose_card`), plug it into the console (`cli.py`) and the web
app (`game_session.py`), and **prove by simulation** that it beats the bots already
in the repo (`HeuristicBot`, `RandomBot`). Then iterate: measure, diagnose,
improve, re-measure.

## 2. Methodology

Each step was driven by scripted tournaments (fixed seeds, `Game` engine
unmodified, 10 donnes per match, cumulative points compared), not by gut feeling:

1. **Baseline.** `HeuristicBot` vs `HeuristicBot` ≈ 50/50 (sane engine);
   `HeuristicBot` team vs `RandomBot` team = 200–0. So beating `HeuristicBot`
   is the real test. Noticed `HeuristicBot` chutes ~25–30 % of its contracts —
   it bids 80 with weak hands and never bids above 90, never coinches.
2. **v1: richer bot, worse results.** First `SparkBot` lost 27–173 with a 68 %
   chute rate. Instead of guessing, I **isolated the two halves** with hybrid
   bots (`Spark bidding + Heuristic cards`, `Heuristic bidding + Spark cards`):
   Spark *card play* alone won 85–65, Spark *bidding* alone lost 50–100.
   Conclusion: bidding was the bug, card play was already an improvement.
3. **Calibrate, don't guess.** Logged 800+ donnes: declarer's hand score vs
   actual RAW trick points and success rate, per bid level. Two key findings:
   - The v1 score→level mapping was wrong: it mapped "P(success at 80)" to
     "bid 150". High bids (130–170, capot) failed ~70–90 % of the time.
     Measured capot success was ~10 % → **never bid capot, cap at 120**.
   - Correct mapping from data (Spark-team declarers):
     score 65 → avg 118 (P≥90 = 82 %), 75 → avg 121 (P≥100 = 79 %),
     85 → avg 135 (P≥110 = 91 %), 90 → avg 141 (P≥120 = 83 %).
     Since a chute gives the opponents 160 + contract, every level targets
     ~75–80 %+ success (breakeven ≈ 65–70 %).
4. **v2–v4: fix bidding discipline, then bidding shape.**
   - Strict thresholds + max 120 + no capot + strict coinche → 158–42.
   - Found Spark's 80-openers were systematically stolen (opponents bid 90
     over them and made 70 %). With P(≥90) ≈ 80 %+ at the entry threshold,
     opening 80 is dominated: **open 90 directly** (better payout, denies
     cheap entry) → 258–42.
   - Added the missing reply: partner may **change suit** with a
     self-sufficient hand (≥72), and support-raises are capped at +10/110.
5. **Validate.** Both seatings, full games to 1000, vs Random, 4×Spark
   stability table, synthetic coinche/surcoinche tests, speed check.

## 3. What the bot does

**Bidding** (`_evaluate` + `_score_to_bid` + `choose_bid`):
- Evaluates every suit: trump points + length bonus (5+ trumps) / penalty
  (≤2 trumps), Valet/Neuf/As honours, belote K+Q (+8, the 20 pts are near
  certain), side Aces (+7), guarded 10s (+5), voids/singletons for cutting.
- Opens 90 (≥63) / 100 (≥77) / 110 (≥83) / 120 (≥88); needs 3+ trumps; never
  capot, never above 120.
- Over partner: raise with 3+ trumps (capped), or speak a new suit if
  self-sufficient (≥72). Never steals partner's suit.
- Over opponents: overbid only with margin (≥63, capped 110 — winner's curse);
  **coinche** only holding their suit (3+ trumps, 2+ honours, defensive score
  ≥62, contract < 110 — measured 7/9 successful); **surcoinche** only when
  still solid (≥77, ≥72 over partner).

**Card play** (tracks played cards, voids, team points, belote, points still
needed for the contract):
- Lead: as declarer draws trumps while holding the best remaining one, else
  cashes side Aces/masters; as defender cashes side Aces, never leads trump,
  attacks — and protects naked 10s.
- Following: if partner wins and stays winning → **feeds** points (doomed 10s
  and loose honours first, never a trump or future master); if it can win →
  takes with the cheapest winning card when the trick is rich / late / needed
  for the contract, else ducks cheap (saves Valet/Neuf); if beaten → sheds the
  cheapest non-master card (points given to opponents must be minimised).

## 4. Results

Spark team vs Heuristic team, 10 donnes per match:

| Match | Wins (Spark–Heur) | Avg pts (Spark–Heur) | Chute % (Spark–Heur) |
|---|---|---|---|
| v4, seed 11, 300 matches | **258–42** | 1719–1010 | 16–29 |
| v4, seed 12, 300 matches (mirrored seats) | **263–37** | 1708–1009 | 16–31 |
| Final, seed 2026, 300 matches | **253–47** | 1723–998 | 16–29 |
| Full games to 1000 (2×60 games) | **48–12 / 48–12** | — | — |
| Spark vs Random, 100 matches | **100–0** | 2624–214 | — |

Success by level (v4): 90 → 80–82 %, 100 → 83–84 %, 110 → 86 %, 120 → 89–92 %
— every level is above breakeven. 4×Spark: stable over 60 donnes, ~7 ms/donne
(fast enough for live web play). Existing rule tests (`tests/test_rules.py`):
16 pass, 2 fail — those 2 coinche-scoring expectations fail identically on the
unmodified codebase (pre-existing, unrelated to the bots).

## 5. Files changed

- **Added `belote/spark_bot.py`** — the `SparkBot(Player)` implementation.
- **`belote/__init__.py`** — export `SparkBot`.
- **`game_session.py`** — web-app bots are now `SparkBot` (was `HeuristicBot`).
- **`cli.py`** — console bots are now `SparkBot` (was `HeuristicBot`).
- Nothing in the rules engine (`cards/bidding/trick/scoring/game`) was touched.

Use it like any bot:

```python
from belote import Game, SparkBot, HeuristicBot
players = {0: SparkBot(0), 1: HeuristicBot(1), 2: SparkBot(2), 3: HeuristicBot(3)}
Game(players, target_score=1000).play_until_end()
```

## 6. Limits & next steps

- Thresholds are calibrated against `HeuristicBot`-level opposition; against
  much stronger humans, re-calibration on real game logs (`DonneLog` already
  records everything needed) would help.
- No Monte-Carlo rollouts or opponent-hand modelling yet — the bot plays its
  own hand + table memory only. A rollout-based declarer (simulate unknown
  cards, ~50 samples) is the natural next upgrade now that the heuristic base
  wins 85 % of matches.
- Annonces (§8) and Sans-Atout/Tout-Atout (§11) remain unimplemented, as before
  (engine limitation, not bot-specific).
