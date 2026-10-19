"""Dernière carte automatique et singletons joués manuellement sur le web.

Lancer depuis la racine : python -B -m unittest discover -s tests -p test_autoplay.py
Nécessite les dépendances web de requirements.txt.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from belote.bidding import ActionType
from belote.cards import Card, Rank, Suit
from belote.trick import TrickState
from game_session import AUTO_CARD_PLAY_DELAY, REDEAL_STAGE_PAUSE, GameSession, NetworkPlayer
from rooms import Room


class AutoplayTests(unittest.TestCase):
    def test_four_passes_collect_then_redeal_before_reopening_bids(self):
        session = GameSession(Room("TEST"), target_score=1000)
        for player in session.players.values():
            player.choose_bid = Mock(side_effect=lambda hand, bidding, legal:
                                     next(action for action in legal if action.type == ActionType.PASSE))
        states, pauses = [], []
        session.broadcast = Mock(side_effect=lambda: states.append(session._build_common()))
        session.sleep = Mock(side_effect=lambda delay: pauses.append((session.ctx.phase, delay)))
        first_dealer = session.game.dealer

        for _ in range(2):
            self.assertTrue(session.game.play_one_donne().annulee)

        stages = [(state["donne_number"], state["phase"]) for state in states]
        collecting = stages.index((1, "donne_annulee"))
        dealing = stages.index((2, "dealing"))
        bidding = stages.index((2, "bidding"))
        self.assertLess(collecting, dealing)
        self.assertLess(dealing, bidding)
        self.assertNotIn((1, "dealing"), stages)
        self.assertEqual([(phase, delay) for phase, delay in pauses if phase != "bidding"],
                         [("donne_annulee", REDEAL_STAGE_PAUSE), ("dealing", REDEAL_STAGE_PAUSE),
                          ("donne_annulee", REDEAL_STAGE_PAUSE)])
        self.assertEqual(states[dealing]["dealer"], (first_dealer - 1) % 4)
        self.assertEqual(states[dealing]["hand_counts"], {str(seat): 8 for seat in range(4)})
        self.assertIsNone(states[dealing]["waiting_kind"])
        self.assertEqual(states[dealing]["bidding_history"], [])
        self.assertNotIn("your_hand", states[dealing])
        self.assertNotIn("hands", states[dealing])
        self.assertEqual(session.game.cumulative_scores, {0: 0, 1: 0})

    def choose(self, hand, plays):
        trick = TrickState(leader=0, atout=Suit.PIQUE, plays=list(plays))
        legal = trick.legal_cards_for(hand)
        session = SimpleNamespace(
            sleep=Mock(),
            _wait_for_choice=Mock(return_value=legal[0]),
        )
        player = NetworkPlayer(trick.current_player, session, "Alice")
        original_hand = list(hand)
        original_plays = list(trick.plays)
        chosen = player.choose_card(hand, trick, legal)
        self.assertIn(chosen, legal)
        self.assertEqual(hand, original_hand)
        self.assertEqual(trick.plays, original_plays)
        return chosen, session, trick

    def assert_automatic(self, hand, plays, expected):
        chosen, session, _ = self.choose(hand, plays)
        self.assertEqual(chosen, expected)
        session._wait_for_choice.assert_not_called()
        session.sleep.assert_called_once_with(AUTO_CARD_PLAY_DELAY)

    def assert_manual(self, hand, plays):
        _, session, trick = self.choose(hand, plays)
        session._wait_for_choice.assert_called_once_with(trick.current_player, "card")
        session.sleep.assert_not_called()

    def test_singleton_of_led_suit_is_manual(self):
        singleton = Card(Rank.SEPT, Suit.COEUR)
        self.assert_manual(
            [singleton, Card(Rank.VALET, Suit.PIQUE)],
            [(0, Card(Rank.AS, Suit.COEUR))],
        )

    def test_singleton_is_manual_when_opponent_has_cut(self):
        singleton = Card(Rank.SEPT, Suit.COEUR)
        self.assert_manual(
            [singleton, Card(Rank.VALET, Suit.PIQUE)],
            [(0, Card(Rank.AS, Suit.COEUR)), (1, Card(Rank.NEUF, Suit.PIQUE))],
        )

    def test_singleton_trump_is_manual_when_trump_is_led(self):
        for rank in (Rank.VALET, Rank.SEPT):
            with self.subTest(rank=rank):
                singleton = Card(rank, Suit.PIQUE)
                self.assert_manual(
                    [singleton, Card(Rank.AS, Suit.COEUR)],
                    [(0, Card(Rank.NEUF, Suit.PIQUE))],
                )

    def test_last_card_follows_automatically(self):
        singleton = Card(Rank.SEPT, Suit.COEUR)
        self.assert_automatic(
            [singleton], [(0, Card(Rank.AS, Suit.COEUR))], singleton,
        )

    def test_several_cards_of_led_suit_require_choice(self):
        self.assert_manual(
            [Card(Rank.SEPT, Suit.COEUR), Card(Rank.DIX, Suit.COEUR)],
            [(0, Card(Rank.AS, Suit.COEUR))],
        )

    def test_forced_raise_with_several_trumps_is_manual(self):
        # Seul le valet est légal, mais ce n'est pas un singleton à l'atout.
        self.assert_manual(
            [Card(Rank.VALET, Suit.PIQUE), Card(Rank.SEPT, Suit.PIQUE)],
            [(0, Card(Rank.NEUF, Suit.PIQUE))],
        )

    def test_last_card_leads_automatically(self):
        last_card = Card(Rank.SEPT, Suit.COEUR)
        self.assert_automatic([last_card], [], last_card)

    def test_leading_with_several_cards_is_manual(self):
        self.assert_manual(
            [Card(Rank.SEPT, Suit.COEUR), Card(Rank.VALET, Suit.PIQUE)], [],
        )

    def test_forced_singleton_cut_is_manual(self):
        self.assert_manual(
            [Card(Rank.VALET, Suit.PIQUE), Card(Rank.AS, Suit.TREFLE)],
            [(0, Card(Rank.AS, Suit.COEUR))],
        )

    def test_partner_winning_allows_discard_instead_of_singleton_cut(self):
        self.assert_manual(
            [Card(Rank.VALET, Suit.PIQUE), Card(Rank.AS, Suit.TREFLE)],
            [(0, Card(Rank.AS, Suit.COEUR)), (1, Card(Rank.SEPT, Suit.COEUR))],
        )

    def test_weak_singleton_trump_does_not_force_undercut(self):
        self.assert_manual(
            [Card(Rank.SEPT, Suit.PIQUE), Card(Rank.AS, Suit.TREFLE)],
            [(0, Card(Rank.AS, Suit.COEUR)), (1, Card(Rank.VALET, Suit.PIQUE))],
        )

    def test_last_card_discards_automatically(self):
        last_card = Card(Rank.AS, Suit.TREFLE)
        self.assert_automatic(
            [last_card], [(0, Card(Rank.AS, Suit.COEUR))], last_card,
        )

    def test_last_card_cuts_automatically(self):
        last_card = Card(Rank.VALET, Suit.PIQUE)
        self.assert_automatic(
            [last_card], [(0, Card(Rank.AS, Suit.COEUR))], last_card,
        )

    def test_last_card_undercuts_automatically(self):
        last_card = Card(Rank.SEPT, Suit.PIQUE)
        self.assert_automatic(
            [last_card],
            [(0, Card(Rank.AS, Suit.COEUR)), (1, Card(Rank.VALET, Suit.PIQUE))],
            last_card,
        )


if __name__ == "__main__":
    unittest.main()
