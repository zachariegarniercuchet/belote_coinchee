"""V4 card play with restrained support after partner changes trump suit."""

from ..bidding import ActionType
from ..cards import Rank, Suit
from ..trick import partner_of, team_of
from .brooklyn_v4 import BrooklynBotV4


class BrooklynBotV5(BrooklynBotV4):
    def _partner_support(self, hand, suit):
        previous, switch = None, None
        if self._auction is not None:
            for seat, action in self._auction.history:
                if team_of(seat) != team_of(self.player_id) or action.type != ActionType.ENCHERE:
                    continue
                if previous is not None and action.suit != previous[1].suit:
                    switch = (previous, (seat, action))
                previous = (seat, action)
        if switch is not None:
            (old_seat, old), (new_seat, entry) = switch
            if (old_seat == self.player_id and new_seat == partner_of(self.player_id)
                    and isinstance(old.suit, Suit) and entry.suit == suit):
                ranks = {c.rank for c in hand if c.suit == suit}
                credit = 10 if Rank.NEUF in ranks else 0
                if {Rank.ROI, Rank.DAME} <= ranks:
                    credit += 20
                # The cheap 80 -> 90 switch still requests side-ace support.
                # Read entry amounts, so subsequent raises cannot reset credit.
                if old.points == 80 and entry.points == 90:
                    credit += 10 * sum(c.rank == Rank.AS and c.suit != suit for c in hand)
                return credit
        return super()._partner_support(hand, suit)
