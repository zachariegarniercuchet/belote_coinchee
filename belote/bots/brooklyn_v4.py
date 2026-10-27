"""V3 bidding/leads, separating attacking trump follows from cuts."""

from .brooklyn_v3 import BrooklynBotV3


class BrooklynBotV4(BrooklynBotV3):
    def choose_card(self, hand, trick_state, legal_cards):
        if (self.is_attacking and trick_state.plays
                and trick_state.plays[0][1].suit == trick_state.atout):
            winning = [c for c in legal_cards
                       if self._hypo_winner(trick_state, c) == self.player_id]
            if winning:
                return min(winning, key=lambda c: c.atout_strength_index())
        # Cutting remains cheapest-winning in attack. Leads and defence keep
        # v3's separate policies; legal compulsory overtrumps still apply.
        return super().choose_card(hand, trick_state, legal_cards)
