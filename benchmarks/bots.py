"""Reproducible web-engine bot comparison, with no running-server changes.

Run from the repo root: .venv/Scripts/python.exe -B benchmarks/bots.py
This is an analysis tool, not another unit-test suite or a bot policy.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belote.bidding import ActionType
from belote.cards import Rank, Suit, ContractMode
from belote.scoring import find_belotes
from game_session import GameSession
from rooms import Room


def play_pair(task):
    brooklyn, opponent, seed, target = task
    records = []
    for team in (0, 1):
        ids = {seat: brooklyn if seat % 2 == team else opponent for seat in range(4)}
        session = GameSession(Room("BENCH"), target_score=target, bot_ids=ids)
        session.game.dealer = seed % 4
        session.game.rng = random.Random(seed)
        session.sleep = lambda seconds: None
        session.broadcast = lambda: None
        leads = {bot: Counter() for bot in (brooklyn, opponent)}
        for seat, player in session.players.items():
            player.rng = random.Random(seed * 17 + seat)
            choose = player.choose_card

            def observe(hand, trick, legal, seat=seat, choose=choose):
                card = choose(hand, trick, legal)
                assert card in legal
                # Analyze AFTER the choice: no hidden information reaches bots.
                if not trick.plays and session.players[seat].is_attacking and isinstance(trick.atout, Suit):
                    enemy_trumps = any(c.suit == trick.atout
                                       for p, cards in session.ctx.hands.items()
                                       if p % 2 != seat % 2 for c in cards)
                    trumps = [c for c in legal if c.suit == trick.atout]
                    sides = [c for c in legal if c.suit != trick.atout]
                    if enemy_trumps and trumps and sides:
                        counts = leads[ids[seat]]
                        counts["opportunities"] += 1
                        counts["trump"] += card.suit == trick.atout
                        counts["side_ace"] += card.suit != trick.atout and card.rank == Rank.AS
                        if any(c.rank == Rank.VALET for c in trumps):
                            counts["jack_opportunities"] += 1
                            counts["jack_led"] += card.suit == trick.atout and card.rank == Rank.VALET
                return card

            player.choose_card = observe
        session.run()
        assert session.finished and session.ctx.phase == "game_end"
        deals = []
        for number, log in enumerate(session.game.donne_logs, 1):
            if log.annulee:
                continue
            contract, result = log.contract, log.result
            assert result is not None and len(log.tricks) == 8
            # Original opener of the team's final suit episode, not necessarily
            # the partner who placed the final contract.
            episode = []
            for seat, action in log.bidding_history:
                if seat % 2 == contract.team and action.type == ActionType.ENCHERE:
                    if episode and episode[-1][1].suit != action.suit:
                        episode = []
                    episode.append((seat, action))
            opener = episode[0][0]
            hand = log.initial_hands[opener]
            trumps = [c for c in hand if c.suit == contract.suit]
            ranks = {c.rank for c in trumps}
            honours = ("both" if {Rank.VALET, Rank.NEUF} <= ranks else
                       "jack_only" if Rank.VALET in ranks else
                       "nine_only" if Rank.NEUF in ranks else "neither")
            deals.append({
                "number": number, "bot": ids[contract.player],
                "bid": contract.points, "made": result.contract_reached,
                "capot": result.capot_team is not None,
                "capot_bid": contract.is_capot,
                "contract_suit": contract.suit.name,
                "margin": None if contract.is_capot else result.total_points[contract.team] - contract.points,
                "failure_net_loss": (result.final_scores[1 - contract.team] - result.final_scores[contract.team]
                                     if not result.contract_reached else None),
                "opening_trumps": len(trumps) if isinstance(contract.suit, Suit) else None,
                "opening_honours": honours if isinstance(contract.suit, Suit) else None,
                "opening_belote": bool(find_belotes({opener: hand}, contract.suit)),
                "opening_belotes": len(find_belotes({opener: hand}, contract.suit)),
                "belote_points": result.belote_points,
            })
        records.append({
            "brooklyn": brooklyn, "opponent": opponent, "seed": seed,
            "brooklyn_team": team, "brooklyn_won": session.winner_team == team,
            "cancelled": len(session.game.donne_logs) - len(deals),
            "deals": deals, "leads": leads,
        })
    return records


def pct(n, d):
    return round(100 * n / d, 1) if d else None


def margin_stats(values):
    if not values:
        return {"n": 0}
    counts = Counter("below_bid" if v < 0 else "0_to_9" if v < 10 else
                     "10_to_20" if v <= 20 else "over_20" for v in values)
    return {"n": len(values), "mean": round(statistics.mean(values), 2),
            "median": statistics.median(values),
            "sd": round(statistics.stdev(values), 2) if len(values) > 1 else None,
            "buckets": {key: {"n": counts[key], "pct": pct(counts[key], len(values))}
                        for key in ("below_bid", "0_to_9", "10_to_20", "over_20")}}


def bootstrap_mean_ci(values):
    # Each value is a SEED PAIR mean/difference. Swap replays and all deals
    # inside a game are dependent; do not treat them as independent trials.
    if len(values) < 2:
        return None
    rng = random.Random(20261020)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(4000))
    return [round(100 * means[99], 1), round(100 * means[3899], 1)]


def summarize(records):
    rows, changes = [], []
    matchups = sorted({(r["brooklyn"], r["opponent"]) for r in records})
    for brooklyn, opponent in matchups:
        games = [r for r in records if (r["brooklyn"], r["opponent"]) == (brooklyn, opponent)]
        all_deals = [d for r in games for d in r["deals"]]
        seed_wins = defaultdict(list)
        for game in games:
            seed_wins[game["seed"]].append(int(game["brooklyn_won"]))
        for bot in (brooklyn, opponent):
            own = [d for d in all_deals if d["bot"] == bot]
            numeric = [d for d in own if d["bid"] is not None]
            suited = [d for d in own if d["opening_trumps"] is not None]
            leads = sum((Counter(r["leads"][bot]) for r in games), Counter())
            by_bid = {}
            by_opening = {}
            for key, selected in (
                ("by_bid", [(str(bid), [d for d in numeric if d["bid"] == bid])
                            for bid in sorted({d["bid"] for d in numeric})]),
                ("by_opening", [(group, [d for d in suited if
                                         f'{d["opening_trumps"]}:{d["opening_honours"]}' == group])
                                for group in sorted({f'{d["opening_trumps"]}:{d["opening_honours"]}' for d in suited})]),
            ):
                dest = by_bid if key == "by_bid" else by_opening
                for group, deals in selected:
                    dest[group] = {"n": len(deals), "made": sum(d["made"] for d in deals),
                                   "made_pct": pct(sum(d["made"] for d in deals), len(deals))}
            wins = sum(r["brooklyn_won"] == (bot == brooklyn) for r in games)
            ci = bootstrap_mean_ci([statistics.mean(v) for v in seed_wins.values()])
            if bot != brooklyn and ci is not None:
                ci = [round(100 - ci[1], 1), round(100 - ci[0], 1)]
            losses = [d["failure_net_loss"] for d in own if not d["made"]]
            by_mode = {}
            for mode in ("SUIT", "SANS_ATOUT", "TOUT_ATOUT"):
                deals = [d for d in own if (d.get("contract_suit") if d.get("contract_suit") in ContractMode.__members__
                                            else "SUIT") == mode]
                bids = [d for d in deals if d["bid"] is not None]
                by_mode[mode] = {
                    "n": len(deals), "made": sum(d["made"] for d in deals),
                    "made_pct": pct(sum(d["made"] for d in deals), len(deals)),
                    "share_of_takes_pct": pct(len(deals), len(own)),
                    "take_pct": pct(len(deals), len(all_deals)),
                    "mean_bid": round(statistics.mean(d["bid"] for d in bids), 2) if bids else None,
                    "margin_all": margin_stats([d["margin"] for d in bids]),
                    "margin_no_capot": margin_stats([d["margin"] for d in bids if not d["capot"]]),
                    "capot_bids": sum(d.get("capot_bid", False) for d in deals),
                    "capot_deals": sum(d["capot"] for d in deals),
                }
            rows.append({
                "bot": bot, "against": opponent if bot == brooklyn else brooklyn,
                "games": len(games), "wins": wins, "win_pct": pct(wins, len(games)),
                "win_ci95_seed_cluster": ci, "played_deals": len(all_deals),
                "cancelled": sum(r["cancelled"] for r in games), "takes": len(own),
                "take_pct": pct(len(own), len(all_deals)), "made": sum(d["made"] for d in own),
                "made_pct": pct(sum(d["made"] for d in own), len(own)),
                "mean_bid": round(statistics.mean(d["bid"] for d in numeric), 2) if numeric else None,
                "margin_all": margin_stats([d["margin"] for d in numeric]),
                "margin_no_capot": margin_stats([d["margin"] for d in numeric if not d["capot"]]),
                "mean_failed_net_loss": round(statistics.mean(losses), 2) if losses else None,
                "by_bid": by_bid, "by_opening": by_opening,
                "by_mode": by_mode,
                "attack_leads": dict(leads),
                "trump_lead_pct": pct(leads["trump"], leads["opportunities"]),
                "side_ace_lead_pct": pct(leads["side_ace"], leads["opportunities"]),
                "jack_lead_pct": pct(leads["jack_led"], leads["jack_opportunities"]),
            })
    for opponent in sorted({r["opponent"] for r in records}):
        pairs = defaultdict(dict)
        for brooklyn in ("brooklyn_v1", "brooklyn_v2"):
            for seed in sorted({r["seed"] for r in records}):
                games = [r for r in records if r["brooklyn"] == brooklyn and
                         r["opponent"] == opponent and r["seed"] == seed]
                if games:
                    pairs[seed][brooklyn] = statistics.mean(int(r["brooklyn_won"]) for r in games)
        differences = [p["brooklyn_v2"] - p["brooklyn_v1"] for p in pairs.values() if len(p) == 2]
        if differences:
            changes.append({"opponent": opponent, "v2_minus_v1_win_pp": round(100 * statistics.mean(differences), 1),
                            "ci95_seed_cluster_pp": bootstrap_mean_ci(differences)})
    return rows, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=50, help="seed pairs per matchup (two full games each)")
    parser.add_argument("--seed", type=int, default=30000)
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--brooklyn", nargs="+", choices=("brooklyn_v1", "brooklyn_v2", "brooklyn_v3", "brooklyn_v4"),
                        default=("brooklyn_v1", "brooklyn_v2"),
                        help="Brooklyn versions to run; defaults preserve the v1/v2 comparison")
    parser.add_argument("--output", type=Path, help="write full reproducible analysis records as JSON")
    args = parser.parse_args()
    if args.pairs < 1 or args.workers < 1 or args.target < 100:
        parser.error("pairs/workers must be positive and target must be at least 100")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tasks = [(b, o, seed, args.target) for b in dict.fromkeys(args.brooklyn)
             for o in ("spark_v2", "spark_v3") for seed in range(args.seed, args.seed + args.pairs)]
    started, records, counts = time.monotonic(), [], Counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(play_pair, task): task for task in tasks}
        for future in as_completed(futures):
            batch = future.result()  # fail visibly; never silently drop games
            records.extend(batch)
            key = (batch[0]["brooklyn"], batch[0]["opponent"])
            counts[key] += len(batch)
            if counts[key] % 20 == 0:
                print(json.dumps({"matchup": key, "games": counts[key],
                                  "elapsed_s": round(time.monotonic() - started, 1)}), file=sys.stderr, flush=True)
    records.sort(key=lambda r: (r["brooklyn"], r["opponent"], r["seed"], r["brooklyn_team"]))
    rows, changes = summarize(records)
    output = {"revision": revision, "pairs_per_matchup": args.pairs,
              "first_seed": args.seed, "target": args.target, "engine": "web",
              "elapsed_s": round(time.monotonic() - started, 2),
              "rows": rows, "changes": changes, "records": records}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "records"}), flush=True)


if __name__ == "__main__":
    main()
