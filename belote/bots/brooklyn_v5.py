"""V4 foundations, suit-switch support and explicit partner priorities."""

from ..bidding import ActionType
from ..cards import Card, ContractMode, Rank, Suit
from ..trick import partner_of, team_of, trick_winner
from .brooklyn_v4 import BrooklynBotV4


class BrooklynBotV5(BrooklynBotV4):
    def _draw_trump(self, hand, trick, legal):
        if (self.is_attacking and self._trump_led
                and sum(c.suit == trick.atout for c in hand) == 1
                and any(c.suit != trick.atout for c in legal)):
            voids = self._known_voids(trick)
            opponents = [p for p in range(4) if team_of(p) != team_of(self.player_id)
                         and trick.atout not in voids[p]]
            possible = sum(any(self.known_card_owner(Card(rank, trick.atout)) in (None, p)
                               for p in opponents)
                           for rank in self._unknown_ranks(trick.atout, hand, trick))
            if possible <= 2:
                # A low-yield hunt is not worth our last trump control merely
                # because partner named the suit first. Publicly located
                # partner cards are not enemy targets; no hidden hands used.
                return None
        return super()._draw_trump(hand, trick, legal)

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
                or trick.atout is ContractMode.TOUT_ATOUT):
            return super().choose_card(hand, trick, legal_cards)
        if (self.is_defending and isinstance(trick.atout, Suit)
                and len(trick.plays) < 3 and trick.plays[0][1].suit != trick.atout):
            # Following a side suit: an exposed 10 is only a current winner.
            # Keep it guarded when an opponent behind can still take it and
            # a cheaper card lets us duck. Do not change trump or SA/TA play.
            winning = [c for c in legal_cards if self._hypo_winner(trick, c) == self.player_id]
            if (winning and all(c.rank == Rank.DIX and c.suit == trick.plays[0][1].suit
                                for c in winning)
                    and not any(self._reasonably_safe(hand, trick, c) for c in winning)):
                losing = [c for c in legal_cards if c not in winning]
                if losing:
                    return self._discard(hand, trick, losing)
        if trick_winner(trick.plays, trick.atout) != partner_of(self.player_id):
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

    def _prior_announcements(self):
        """Our descriptions before the current team episode, from public bids."""
        announced, episode = set(), set()
        current = None
        if self._auction is not None:
            for seat, action in self._auction.history:
                if team_of(seat) != team_of(self.player_id) or action.type != ActionType.ENCHERE:
                    continue
                if action.suit != current:
                    announced.update(episode)
                    episode = set()
                    current = action.suit
                if seat == self.player_id:
                    episode.add(action.suit)
        return announced

    def _mode_support(self, hand, mode):
        announced = self._prior_announcements()
        if announced and mode is ContractMode.TOUT_ATOUT:
            if mode in announced:
                return 0  # All J/9/belotes were already described at TA.
            credit = 0
            for suit in Suit:
                if suit in announced:
                    continue
                ranks = {c.rank for c in hand if c.suit == suit}
                credit += 10 if Rank.VALET in ranks else 0
                if {Rank.ROI, Rank.DAME} <= ranks:
                    credit += 20
            return credit
        if announced and mode is ContractMode.SANS_ATOUT:
            if mode in announced:
                return 0
            credit = super()._mode_support(hand, mode)
            if any(isinstance(suit, Suit) for suit in announced):
                credit -= 10 * sum(c.rank == Rank.AS for c in hand)
            return credit
        return super()._mode_support(hand, mode)

    def _partner_support(self, hand, suit):
        announced = self._prior_announcements()
        if announced:
            if ContractMode.TOUT_ATOUT in announced or suit in announced:
                return 0
            # Earlier SA/suited bids describe the aces, not the new trump's
            # J/9/belote. No exception depends on the auction amounts.
            ranks = {c.rank for c in hand if c.suit == suit}
            credit = 10 * len(ranks & {Rank.VALET, Rank.NEUF})
            if {Rank.ROI, Rank.DAME} <= ranks:
                credit += 20
            return credit
        return super()._partner_support(hand, suit)
