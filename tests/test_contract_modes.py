"""Representative SA/TA journeys, from the repository PDF (§11)."""

import unittest

from belote.bidding import BidAction, BiddingState
from belote.cards import Card, ContractMode, Rank, Suit, full_deck
from belote.claim import find_claim, play_claim
from belote.trick import TrickState, legal_cards, trick_winner
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


if __name__ == '__main__':
    unittest.main()
