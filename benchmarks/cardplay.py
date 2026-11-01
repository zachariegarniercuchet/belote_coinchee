"""Duplicate-board card-play comparison with a frozen public auction.

The web engine is unchanged: only its auction choices are forced to a common
legal history, after each real bot has observed that history with its own hand.
"""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belote.bidding import BiddingState
from belote.bots import create_bot
from belote.cards import Suit, cut_deck, deal, new_shuffled_deck
from game_session import GameSession
from rooms import Room
from serialize import bid_action_to_dict, card_id

VERSIONS = ('brooklyn_v1', 'brooklyn_v3', 'brooklyn_v4')
REFERENCES = ('brooklyn_v1', 'brooklyn_v4')
OPPONENTS = ('spark_v2', 'spark_v3')


def common_auction(seed, team, opponent, reference):
    dealer = seed % 4
    rng = random.Random(seed)
    hands = deal(cut_deck(new_shuffled_deck(rng), rng), (dealer - 1) % 4)
    bidders = {p: create_bot(reference if p % 2 == team else opponent, p)
               for p in range(4)}
    for p, bidder in bidders.items():
        bidder.rng = random.Random(seed * 17 + p)
        bidder.notify_donne_start()
    state = BiddingState(dealer)
    while not state.finished:
        p = state.current_player
        legal = state.legal_actions()
        action = bidders[p].choose_bid(list(hands[p]), state, legal)
        assert action in legal
        state.apply(action)
    return hands, state


def replay(seed, team, opponent, version, hands, frozen):
    session = GameSession(Room('DUPLICATE'), target_score=1000,
                          bot_ids={p: version if p % 2 == team else opponent for p in range(4)})
    session.game.dealer = seed % 4
    session.game.rng = random.Random(seed)
    session.sleep = lambda _: None
    session.broadcast = lambda: None
    for p, player in session.players.items():
        player.rng = random.Random(seed * 17 + p)
        observe = player.choose_bid

        def forced(hand, state, legal, p=p, observe=observe):
            # Populate normal own-hand/public-auction memories; never pass
            # another seat's hand or let the proposed bid alter this replay.
            observe(list(hand), state, list(legal))
            seat, action = frozen.history[len(state.history)]
            assert seat == p and action in legal
            return action

        player.choose_bid = forced
    log = session.game.play_one_donne()
    assert log.initial_hands == hands
    assert log.bidding_history == frozen.history
    assert log.contract == frozen.contract
    assert log.result is not None and len(log.tricks) == len(log.trick_winners) == 8
    return log


def record_result(log, team):
    result = log.result
    return {
        'card_points': result.raw_points[team],
        'earned_points': result.total_points[team],
        'awarded_points': result.final_scores[team],
        'net_awarded': result.final_scores[team] - result.final_scores[1 - team],
        'contract_made': result.contract_reached,
        'capot_team': result.capot_team,
        'tricks_won': sum(p % 2 == team for p in log.trick_winners),
        'tricks': [[[p, card_id(c)] for p, c in trick] for trick in log.tricks],
        'winners': log.trick_winners,
    }


def first_change(baseline, other, team, suit):
    for trick_no, (before, after) in enumerate(zip(baseline['tricks'], other['tricks']), 1):
        for position, (old, new) in enumerate(zip(before, after)):
            if old != new:
                assert old[0] == new[0] and old[0] % 2 == team
                kind = 'last_trump_lead' if position == 0 else 'winning_requested_trump'
                if position:
                    assert before[0][1].split('_', 1)[1] == suit
                return {'trick': trick_no, 'position': position, 'seat': old[0],
                        'before': old[1], 'after': new[1], 'kind': kind}
    return None


def play_seed(task):
    seed, controls = task
    records, cache = [], {}
    for reference in REFERENCES:
        for opponent in OPPONENTS:
            for team in (0, 1):
                hands, state = common_auction(seed, team, opponent, reference)
                c = state.contract
                kind = ('cancelled' if c is None else
                        'attack_suit' if isinstance(c.suit, Suit) and c.team == team else
                        'defense_suit' if isinstance(c.suit, Suit) else c.suit.name)
                row = {
                    'seed': seed, 'team': team, 'reference': reference,
                    'opponent': opponent, 'dealer': seed % 4,
                    'leader': (seed - 1) % 4, 'kind': kind,
                    'hand_fingerprint': hashlib.sha256(json.dumps(
                        {p: [card_id(card) for card in hand] for p, hand in hands.items()},
                        sort_keys=True).encode()).hexdigest(),
                    'auction': [{'seat': p, 'turn': i,
                                 **{k: v for k, v in bid_action_to_dict(a, 0).items() if k != 'index'}}
                                for i, (p, a) in enumerate(state.history)],
                    'contract': None if c is None else {
                        'player': c.player, 'team': c.team, 'suit': c.suit.name,
                        'points': c.points, 'capot': c.is_capot,
                        'coinche': c.coinche_state.name, 'coinche_by_team': c.coinche_by_team},
                    'outcomes': {},
                    'reused_identical_replay': False,
                }
                if c is not None and (kind == 'attack_suit' or controls):
                    key = (opponent, team, tuple(state.history))
                    if key in cache:
                        row['outcomes'] = copy.deepcopy(cache[key])
                        row['reused_identical_replay'] = True
                        records.append(row)
                        continue
                    logs = {v: replay(seed, team, opponent, v, hands, state) for v in VERSIONS}
                    if kind != 'attack_suit':
                        baseline = logs[VERSIONS[0]]
                        # These card policies are common: a divergence is a
                        # wiring/information bug, not an estimated advantage.
                        for other in list(logs.values())[1:]:
                            assert other.tricks == baseline.tricks
                            assert other.result == baseline.result
                    row['outcomes'] = {v: record_result(log, team) for v, log in logs.items()}
                    if kind == 'attack_suit':
                        baseline = row['outcomes']['brooklyn_v1']
                        for version in VERSIONS:
                            change = first_change(baseline, row['outcomes'][version], team, c.suit.name)
                            if version == 'brooklyn_v3' and change:
                                assert change['kind'] == 'last_trump_lead'
                            row['outcomes'][version]['first_change'] = change
                        follow_change = first_change(row['outcomes']['brooklyn_v3'],
                                                     row['outcomes']['brooklyn_v4'], team, c.suit.name)
                        if follow_change:
                            assert follow_change['kind'] == 'winning_requested_trump'
                        row['outcomes']['brooklyn_v4']['first_change_vs_v3'] = follow_change
                    cache[key] = row['outcomes']
                records.append(row)
    return records


def summarize(records):
    primary = [r for r in records if r['kind'] == 'attack_suit']
    result = {}
    for version in VERSIONS:
        outcomes = [r['outcomes'][version] for r in primary]
        differences = [(r['outcomes'][version], r['outcomes']['brooklyn_v1']) for r in primary]
        result[version] = {
            'n': len(outcomes), 'made': sum(o['contract_made'] for o in outcomes),
            'mean_earned_points': sum(o['earned_points'] for o in outcomes) / len(outcomes) if outcomes else None,
            'mean_net_awarded': sum(o['net_awarded'] for o in outcomes) / len(outcomes) if outcomes else None,
            'better_points': sum(o['earned_points'] > b['earned_points'] for o, b in differences),
            'equal_points': sum(o['earned_points'] == b['earned_points'] for o, b in differences),
            'worse_points': sum(o['earned_points'] < b['earned_points'] for o, b in differences),
            'saved_contracts': sum(o['contract_made'] and not b['contract_made'] for o, b in differences),
            'lost_contracts': sum(b['contract_made'] and not o['contract_made'] for o, b in differences),
        }
    return result


def write_result(path, output):
    """Keep full traces in standard JSON without megabytes of indentation."""
    metadata = {k: v for k, v in output.items() if k != 'records'}
    records = output['records']
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(metadata, ensure_ascii=True, indent=2)[:-1].rstrip() + ',\n  "records": [\n')
        for i, row in enumerate(records):
            stream.write('    ' + json.dumps(row, ensure_ascii=True, separators=(',', ':')))
            stream.write(',\n' if i + 1 < len(records) else '\n')
        stream.write('  ]\n}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=500)
    parser.add_argument('--seed', type=int, default=50000)
    parser.add_argument('--control-seeds', type=int, default=50,
                        help='Replay defense/SA/TA controls on the first N seeds; main attack boards always replayed')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1 or args.workers < 1 or not 0 <= args.control_seeds <= args.seeds:
        parser.error('Positive seeds/workers and control-seeds between zero and seeds required')
    # V2 has the same card-play methods as V1; its bidding is deliberately
    # neutralized here, so rerunning it would duplicate the same policy.
    v1, v2 = (create_bot(v, 0) for v in ('brooklyn_v1', 'brooklyn_v2'))
    assert v1.choose_card.__func__ is v2.choose_card.__func__
    assert v1._draw_trump.__func__ is v2._draw_trump.__func__
    v3, v4 = (create_bot(v, 0) for v in ('brooklyn_v3', 'brooklyn_v4'))
    assert v3._draw_trump.__func__ is v4._draw_trump.__func__
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    start, records, completed = time.monotonic(), [], 0
    tasks = [(seed, seed < args.seed + args.control_seeds)
             for seed in range(args.seed, args.seed + args.seeds)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_seed, task) for task in tasks]
        for future in as_completed(futures):
            records.extend(future.result())
            completed += 1
            if completed % 25 == 0 or completed == args.seeds:
                print(json.dumps({'seeds': completed, 'of': args.seeds,
                                  'elapsed_s': round(time.monotonic() - start, 1)}), file=sys.stderr, flush=True)
    records.sort(key=lambda r: (r['seed'], r['reference'], r['opponent'], r['team']))
    output = {'revision': revision, 'engine': 'web', 'first_seed': args.seed,
              'seeds': args.seeds, 'control_seeds': args.control_seeds,
              'references': REFERENCES, 'opponents': OPPONENTS, 'versions': VERSIONS,
              'elapsed_s': round(time.monotonic() - start, 2),
              'summary': summarize(records), 'records': records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_result(args.output, output)
    print(json.dumps(output['summary']), flush=True)


if __name__ == '__main__':
    main()
