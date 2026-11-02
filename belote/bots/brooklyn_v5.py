"""V4 foundations, suit-switch support and explicit partner priorities."""

from ..bidding import ActionType
from ..cards import Card, ContractMode, Rank, Suit
from ..trick import partner_of, team_of, trick_winner
from .brooklyn_v4 import BrooklynBotV4


class BrooklynBotV5(BrooklynBotV4):
    def _bank_partner_points(self, hand, trick, legal):
        """Last defender: bank vulnerable points, including by overtaking."""
        atout = trick.atout
        tens = {c.suit for c in hand if c.rank == Rank.DIX}
        voids = self._known_voids(trick)
        unknown_trumps = self._unknown_ranks(atout, hand, trick) if isinstance(atout, Suit) else set()

        def preserve(card):
            if card.rank == Rank.AS and card.suit != atout:
                if card.suit in tens:
                    return False  # Cash A while keeping our 10 next.
                endangered = len(hand) <= 2 and bool(unknown_trumps) and any(
                    team_of(p) != team_of(self.player_id) and card.suit in voids[p]
                    and atout not in voids[p]
                    and any(self.known_card_owner(Card(rank, atout)) in (None, p)
                            for rank in unknown_trumps) for p in range(4))
                return not endangered
            # Also preserve a sequence covered by our own higher cards.
            return not any(self._strength(Card(rank, card.suit), atout) < self._strength(card, atout)
                           for rank in self._unknown_ranks(card.suit, hand, trick))

        disposable = [c for c in legal if not preserve(c)]
        if disposable:
            return max(disposable, key=lambda c: (
                c.points(atout), sum(h.suit == c.suit for h in hand) == 1,
                self._strength(c, atout)))
        # All legal cards are protected: one still has to be played.
        return min(legal, key=lambda c: (c.points(atout), -self._strength(c, atout)))

    def choose_card(self, hand, trick_state, legal_cards):
        trick = trick_state
        if (len(legal_cards) <= 1 or not trick.plays
                or trick.atout is ContractMode.TOUT_ATOUT
                or trick_winner(trick.plays, trick.atout) != partner_of(self.player_id)):
            return super().choose_card(hand, trick, legal_cards)
        if len(trick.plays) == 3:
            if self.is_defending:
                return self._bank_partner_points(hand, trick, legal_cards)
            return super().choose_card(hand, trick, legal_cards)

        staying = [c for c in legal_cards if self._hypo_winner(trick, c) == partner_of(self.player_id)]
        if not staying:
            return super().choose_card(hand, trick, legal_cards)  # Forced to overtake.
        if isinstance(trick.atout, Suit) and trick.plays[0][1].suit != trick.atout:
            # Do not voluntarily cut/overcut a winning partner before last seat.
            # Lack of certainty about partner is not a reason to spend trump.
            non_cut = [c for c in legal_cards
                       if c.suit != trick.atout or c in staying]
            legal_cards = non_cut
        winning_masters = [c for c in legal_cards if self._hypo_winner(trick, c) == self.player_id
                           and self._is_master(c, trick.atout, trick)]
        if not winning_masters:
            # Do not put 10 on partner's K with A still missing behind us.
            return super().choose_card(hand, trick, staying)
        return super().choose_card(hand, trick, legal_cards)

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
