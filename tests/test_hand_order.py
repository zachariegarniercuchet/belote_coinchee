"""Tri des mains et changement d'ordre à la fin des enchères.

python -B -m unittest discover -s tests -p test_hand_order.py
"""

import itertools
import unittest

from belote.bidding import BiddingState, BidAction
from belote.cards import Card, Rank, Suit, ATOUT_ORDER, NONATOUT_ORDER
from game_session import GameSession
from rooms import Room
from serialize import RED_SUITS, sorted_hand


class HandOrderTests(unittest.TestCase):
    def test_normal_and_trump_strength_for_every_suit(self):
        for suit in Suit:
            with self.subTest(suit=suit):
                hand = [Card(rank, suit) for rank in Rank]
                original = list(hand)
                self.assertEqual([c.rank for c in sorted_hand(hand)], NONATOUT_ORDER)
                self.assertEqual([c.rank for c in sorted_hand(hand, suit)], ATOUT_ORDER)
                self.assertEqual(hand, original)

    def test_only_trump_ranks_change(self):
        hand = [Card(rank, suit) for suit in Suit for rank in Rank]
        for atout in Suit:
            ordered = sorted_hand(hand, atout)
            for suit in Suit:
                expected = ATOUT_ORDER if suit == atout else NONATOUT_ORDER
                self.assertEqual([card.rank for card in ordered if card.suit == suit], expected)

    def test_four_suits_follow_spades_hearts_clubs_diamonds(self):
        hand = [Card(Rank.AS, suit) for suit in Suit]
        self.assertEqual([card.suit for card in sorted_hand(hand)],
                         [Suit.PIQUE, Suit.COEUR, Suit.TREFLE, Suit.CARREAU])

    def test_best_color_separation_for_every_suit_subset(self):
        for size in range(1, 5):
            for suits in itertools.combinations(Suit, size):
                hand = [Card(rank, suit) for suit in suits for rank in (Rank.SEPT, Rank.AS)]
                for atout in (None, *Suit):
                    with self.subTest(suits=suits, atout=atout):
                        ordered = sorted_hand(hand, atout)
                        groups = [suit for suit, _ in itertools.groupby(card.suit for card in ordered)]
                        colors = [suit.name in RED_SUITS for suit in groups]
                        different_neighbors = sum(left != right for left, right in zip(colors, colors[1:]))
                        expected = size - 1 if len(set(colors)) == 2 else 0
                        self.assertEqual(different_neighbors, expected)
                        self.assertCountEqual(ordered, hand)
                        self.assertEqual(ordered, sorted_hand(list(reversed(hand)), atout))

    def test_empty_hand(self):
        self.assertEqual(sorted_hand([]), [])

    def test_trump_order_starts_only_after_bidding_finishes(self):
        session = GameSession(Room("TEST"), target_score=1000)
        bidding = session.ctx.bidding_state = BiddingState(dealer=0)
        session.ctx.hands[0] = [Card(rank, Suit.PIQUE) for rank in Rank]
        original = list(session.ctx.hands[0])
        bidding.apply(BidAction.enchere(80, Suit.PIQUE))
        before = session._build_for_player(session._build_common(), 0)
        self.assertEqual([card["rank"] for card in before["your_hand"]],
                         [rank.value for rank in NONATOUT_ORDER])
        while not bidding.finished:
            bidding.apply(BidAction.passe())
        after = session._build_for_player(session._build_common(), 0)
        self.assertEqual([card["rank"] for card in after["your_hand"]],
                         [rank.value for rank in ATOUT_ORDER])
        self.assertEqual(session.ctx.hands[0], original)


if __name__ == "__main__":
    unittest.main()
