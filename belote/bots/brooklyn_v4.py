"""V3 bidding/leads, with protection for held masters on requested trump."""

from .brooklyn_v3 import BrooklynBotV3


class BrooklynBotV4(BrooklynBotV3):
    def choose_card(self, hand, trick_state, legal_cards):
        if trick_state.plays and trick_state.plays[0][1].suit == trick_state.atout:
            winning = [c for c in legal_cards
                       if self._hypo_winner(trick_state, c) == self.player_id]
            if self.is_attacking and len(trick_state.plays) < 3 and winning:
                # Before last seat, cash the biggest sure winner. If a higher
                # enemy trump may still follow, risk only the smallest winner.
                safe = [c for c in winning if self._reasonably_safe(hand, trick_state, c)]
                if safe:
                    return max(safe, key=lambda c: c.points(trick_state.atout))
                return max(winning, key=lambda c: c.atout_strength_index())
            if any(c.suit == trick_state.atout and self._is_master(c, trick_state.atout, trick_state)
                   for c in hand):
                # Cash a vulnerable lower trump while keeping our sure winner.
                # Legal cards already impose climbing; a forced master is used.
                # If climbing is impossible, spare the next master likewise.
                # In attack, only last seat can bank the trick this way.
                return max(legal_cards, key=lambda c: c.atout_strength_index())
            if winning:
                return max(winning, key=lambda c: c.points(trick_state.atout))
        # Leads and cuts retain their own policies.
        return super().choose_card(hand, trick_state, legal_cards)
