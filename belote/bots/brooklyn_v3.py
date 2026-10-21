"""V1's individual hand valuation plus explicit partnership support credits."""

from ..cards import Rank
from .brooklyn_v2 import BrooklynBotV2


class BrooklynBotV3(BrooklynBotV2):
    """Keep v1's entry ambition, then add the partner's unspent strength.

    The opener's aces, belote and distribution are already in v1's valuation:
    never add them again as v2 entry/rebid bonuses. Public-history accounting,
    suit switches and card play are inherited unchanged.
    """

    def _opening_value(self, hand, suit):
        score, detail = self._evaluate(hand, suit)
        return self._score_to_bid(score, detail["trumps"])

    def _entry_bonus(self, hand, suit):
        return 0

    def _rebid_bonus(self, hand, suit):
        return 0

    @staticmethod
    def _partner_support(hand, suit):
        ranks = {c.rank for c in hand if c.suit == suit}
        # V1 can open without J/9, so BOTH honours may be new information.
        honours = len(ranks & {Rank.VALET, Rank.NEUF})
        aces = sum(c.rank == Rank.AS and c.suit != suit for c in hand)
        belote = 20 if {Rank.ROI, Rank.DAME} <= ranks else 0
        return 10 * (honours + aces) + belote
