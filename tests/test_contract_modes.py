"""Representative SA/TA journeys, from the repository PDF (§11)."""

import unittest
import copy
import random
from unittest.mock import Mock, patch

from belote.bidding import BidAction, BiddingState, Contract, CoincheState
from belote.bots import BOT_REGISTRY, create_bot
from belote.cards import Card, ContractMode, Rank, Suit, full_deck
from belote.claim import find_claim, play_claim
from belote.trick import TrickState, legal_cards, trick_winner
from belote.game import Donne
from belote.scoring import find_belotes, belote_points_by_team, compute_donne_score
from game_session import GameSession
from rooms import Room
from serialize import sorted_hand


SA, TA = ContractMode.SANS_ATOUT, ContractMode.TOUT_ATOUT


def cards(*codes):
    return [Card(Rank(rank), Suit[suit]) for rank, suit in (code.split('_') for code in codes)]


class ContractModeTests(unittest.TestCase):
    def test_bidding_and_play_without_cutting(self):
        self.assertEqual(len(full_deck()), 32)  # SA/TA must never become card suits.
        for mode, values, winner in ((SA, (19, 10, 4, 3, 2, 0, 0, 0), 0),
                                     (TA, (13, 9, 6, 5, 3, 2, 0, 0), 1)):
            with self.subTest(mode=mode):
                state = BiddingState(dealer=1)
                state.apply(BidAction.enchere(80, mode))
                for _ in range(3):
                    state.apply(BidAction.passe())
                self.assertTrue(state.finished)
                self.assertEqual(state.contract.suit, mode)
                ordered = sorted_hand(cards('A_COEUR', '10_COEUR', 'R_COEUR', 'D_COEUR',
                                            'V_COEUR', '9_COEUR', '8_COEUR', '7_COEUR'), mode)
                self.assertEqual(tuple(c.points(mode) for c in ordered), values)
                self.assertEqual(sum(c.points(mode) for c in full_deck()), 152)
                plays = list(enumerate(cards('A_COEUR', 'V_COEUR', '9_COEUR', 'V_PIQUE')))
                self.assertEqual(trick_winner(plays, mode), winner)  # Off-suit J never cuts.
                hand = cards('V_COEUR', '7_COEUR', 'V_PIQUE')
                legal = legal_cards(hand, [(3, cards('A_COEUR')[0])], mode, 0)
                self.assertEqual(legal, hand[:1] if mode is TA else hand[:2])
                # Partner holds the trick: TA still requires climbing, SA does not.
                legal = legal_cards(hand, [(2, cards('A_COEUR')[0]), (3, cards('7_TREFLE')[0])], mode, 0)
                self.assertEqual(legal, hand[:1] if mode is TA else hand[:2])
                self.assertEqual(legal_cards(hand, [(3, cards('A_CARREAU')[0])], mode, 0), hand)
                masters = {0: ordered[:2], 1: cards('8_PIQUE', '7_PIQUE'),
                           2: ordered[2:4], 3: cards('8_TREFLE', '7_TREFLE')}
                claim = find_claim(masters, 0, mode)
                self.assertIsNotNone(claim)
                self.assertEqual([t.winner() for t in play_claim(masters, 0, mode, claim)], [0, 0])

    def test_complete_deals_scores_announcements_and_review(self):
        # Each of the four players owns one K/Q pair; other cards are shared.
        hands = {p: [Card(r, s) for r in (Rank.ROI, Rank.DAME)] for p, s in enumerate(Suit)}
        rest = [c for c in full_deck() if c.rank not in (Rank.ROI, Rank.DAME)]
        random.Random(17).shuffle(rest)
        for i, card in enumerate(rest):
            hands[i % 4].append(card)
        for mode in (SA, TA):
            for bot_id in BOT_REGISTRY:
                def players():
                    bots = {p: create_bot(bot_id, p) for p in range(4)}
                    for p, bot in bots.items():
                        bot.rng.seed(p + 32)
                        bot.choose_bid = lambda hand, state, legal: (
                            BidAction.enchere(80, mode) if state.contract is None else BidAction.passe())
                    return bots
                with self.subTest(mode=mode, bot=bot_id):
                    with patch('belote.game.deal', side_effect=lambda *_: copy.deepcopy(hands)):
                        console = Donne(players(), dealer=0).play()
                    session = GameSession(Room('MODES'), target_score=1000)
                    session.game.players = players()
                    session.game.dealer = 0
                    session.sleep = Mock()
                    states = []
                    session.broadcast = lambda: states.append(copy.deepcopy(session._build_common()))
                    with patch('game_session.deal', side_effect=lambda *_: copy.deepcopy(hands)):
                        web = session.game.play_one_donne()
                    self.assertEqual(console.tricks, web.tricks)
                    self.assertEqual(console.result, web.result)
                    self.assertEqual(len(web.tricks), 8)
                    self.assertEqual(sum(web.result.raw_points.values()), 152)
                    expected = {0: 40, 1: 40} if mode is TA else {0: 0, 1: 0}
                    self.assertEqual(web.result.belote_points, expected)
                    self.assertEqual(belote_points_by_team(find_belotes(hands, mode)), expected)
                    for t in (0, 1):
                        dix = 100 if web.result.capot_team is not None else 10
                        self.assertEqual(web.result.total_points[t], web.result.raw_points[t] +
                                         (dix if web.result.dix_de_der_team == t else 0) + expected[t])
                    by_suit = {}
                    for entry in session.ctx.belote_announcements:
                        by_suit.setdefault(entry['suit'], []).append(entry['label'])
                    self.assertTrue(all(labels in (['Belote !'], ['Belote !', 'Rebelote !'])
                                        for labels in by_suit.values()))
                    if mode is SA:
                        self.assertEqual(by_suit, {})
                    else:
                        self.assertTrue(by_suit)
                    for state in states:
                        if state['last_donne_result'] is None:
                            # Only the pairs actually announced may become public.
                            announced = {e['suit'] for e in state['belote_announcements']}
                            visible = belote_points_by_team({s:p for s,p in find_belotes(hands, mode).items()
                                                            if s.name in announced})
                            self.assertEqual(state['belote_points'], {str(t):visible[t] for t in (0, 1)})
                        if state['phase'] not in ('donne_end', 'game_end'):
                            self.assertEqual(state['completed_deals'], [])
                    session.ctx.phase = 'donne_end'
                    review = session._build_common()['completed_deals'][0]
                    self.assertEqual(review['contract']['suit'], mode.name)
                    self.assertEqual(len(review['tricks']), 8)
        # Four belotes may all belong to one camp and finance a TA contract.
        all_pairs = {0: [c for c in full_deck() if c.rank in (Rank.ROI, Rank.DAME)]}
        self.assertEqual(belote_points_by_team(find_belotes(all_pairs, TA)), {0:80, 1:0})
        contract = Contract(0, 0, 240, TA, False)
        result = compute_donne_score(contract, {0:152, 1:0}, 0, None, None, {0:80, 1:0})
        self.assertTrue(result.contract_reached)
        self.assertEqual(result.total_points, {0:242, 1:0})
        # All belotes remain imprenables, also when a coinched contract falls.
        contract.coinche_state = CoincheState.COINCHE
        result = compute_donne_score(contract, {0:50, 1:102}, 1, None, None, {0:40, 1:40})
        self.assertFalse(result.contract_reached)
        self.assertEqual(result.score_before_rounding, {0:40, 1:840})


if __name__ == '__main__':
    unittest.main()
