"""V3 bidding, scoped attacking trump play and last-trump control."""

from .brooklyn_v3 import BrooklynBotV3


class BrooklynBotV4(BrooklynBotV3):
    def _draw_trump(self, hand, trick, legal):
        if (self.is_attacking and self._trump_led
                and sum(c.suit == trick.atout for c in hand) == 1
                and any(c.suit != trick.atout for c in legal)):
            # Once drawing has started, keep the last trump for control/dix
            # de der, even if partner opened. This only affects our own lead.
            return None
        return super()._draw_trump(hand, trick, legal)

    def choose_card(self, hand, trick_state, legal_cards):
        if (self.is_attacking and trick_state.plays
                and trick_state.plays[0][1].suit == trick_state.atout):
            winning = [c for c in legal_cards
                       if self._hypo_winner(trick_state, c) == self.player_id]
            if winning:
                return min(winning, key=lambda c: c.atout_strength_index())
        # Cutting remains cheapest-winning in attack. Defence is unchanged;
        # leads use the separate policy above. Compulsory overtrumps apply.
        return super().choose_card(hand, trick_state, legal_cards)
