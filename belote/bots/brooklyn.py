"""David's point-first, trump-drawing rules. Bidding is inherited from Spark.

Only our hand, the contract and public plays are available to these rules.
Existing Spark versions are deliberately left unchanged.
"""

from __future__ import annotations

from ..cards import Card, Rank
from ..trick import TrickState, partner_of, team_of, trick_winner
from .spark import SparkBot


class BrooklynBot(SparkBot):
    """Cash valuable winners; draw opponents' trumps on the declaring team."""

    def _infer_voids(self, plays):
        voids = []
        if not plays:
            return voids
        led = plays[0][1].suit
        for i, (seat, card) in enumerate(plays[1:], 1):
            if card.suit == led:
                continue  # Following suit says nothing about the player's trumps.
            voids.append((seat, led))
            if led != self.atout and card.suit != self.atout:
                winner = trick_winner(plays[:i], self.atout)
                winner_card = next(c for p, c in plays[:i] if p == winner)
                # No cut while an opponent wins WITHOUT trump proves no trump.
                # Discarding on partner, or declining an impossible overcut, does not.
                if team_of(winner) != team_of(seat) and winner_card.suit != self.atout:
                    voids.append((seat, self.atout))
        return voids

    def _known_voids(self, trick):
        voids = {seat: set(suits) for seat, suits in self.void_suits.items()}
        for seat, suit in self._infer_voids(trick.plays):
            voids[seat].add(suit)
        return voids

    def _unknown_ranks(self, suit, hand, trick):
        known = self._played_ranks(suit, trick) | {c.rank for c in hand if c.suit == suit}
        return set(Rank) - known

    def _opponents_have_trumps(self, hand, trick):
        if not self._unknown_ranks(trick.atout, hand, trick):
            return False
        voids = self._known_voids(trick)
        return any(trick.atout not in voids[seat] for seat in range(4)
                   if team_of(seat) != team_of(self.player_id))

    @staticmethod
    def _strength(card, atout):
        return card.atout_strength_index() if card.suit == atout else card.nonatout_strength_index()

    def _reasonably_safe(self, hand, trick, card):
        """No known cut or possible higher card from opponents still to play.

        An unshown void is not treated as a certain cut: cashing a first-round
        ace remains sensible. This is a heuristic, NOT a guarantee of winning.
        """
        plays = trick.plays + [(self.player_id, card)]
        winner = trick_winner(plays, trick.atout)
        best = next(c for seat, c in plays if seat == winner)
        voids = self._known_voids(trick)
        higher = {rank for rank in self._unknown_ranks(best.suit, hand, trick)
                  if self._strength(Card(rank, best.suit), trick.atout)
                  < self._strength(best, trick.atout)}
        unknown_trumps = self._unknown_ranks(trick.atout, hand, trick)
        for offset in range(1, 4 - len(trick.plays)):
            seat = (self.player_id + offset) % 4
            if team_of(seat) == team_of(self.player_id):
                continue
            if best.suit not in voids[seat] and higher:
                return False
            if (best.suit != trick.atout and best.suit in voids[seat]
                    and trick.atout not in voids[seat] and unknown_trumps):
                return False
        return True

    def _draw_trump(self, hand, trick, legal):
        trumps = [c for c in legal if c.suit == trick.atout]
        if not self.is_attacking or not trumps or not self._opponents_have_trumps(hand, trick):
            return None
        jack = next((c for c in trumps if c.rank == Rank.VALET), None)
        if jack is not None:
            return jack
        best = min(trumps, key=lambda c: c.atout_strength_index())
        if self._is_master(best, trick.atout, trick):
            # In particular, the nine follows the jack when it is now master.
            return best
        # Missing jack/nine: make them fall with a small trump, not a sacrifice
        # of the nine under an unseen jack. Even a last small trump may be led.
        return max(trumps, key=lambda c: c.atout_strength_index())

    def _discard(self, hand, trick, legal):
        return min(legal, key=lambda c: (
            c.points(trick.atout), self._keep_value(c, hand, trick.atout, trick),
            -self._strength(c, trick.atout)))

    def _lead(self, hand, trick, legal):
        trump = self._draw_trump(hand, trick, legal)
        if trump is not None:
            return trump
        masters = [c for c in legal if c.suit != trick.atout
                   and self._is_master(c, trick.atout, trick)]
        safe = [c for c in masters if self._reasonably_safe(hand, trick, c)]
        if safe or masters:
            return max(safe or masters, key=lambda c: (
                c.points(trick.atout), sum(h.suit == c.suit for h in hand)))
        side = [c for c in legal if c.suit != trick.atout]
        pool = side or legal
        # Establish a long side suit; defenders do not initiate a trump hunt.
        return min(pool, key=lambda c: (
            -sum(h.suit == c.suit for h in hand),
            c.points(trick.atout), self._keep_value(c, hand, trick.atout, trick)))

    def choose_card(self, hand: list[Card], trick_state: TrickState,
                    legal_cards: list[Card]) -> Card:
        if len(legal_cards) == 1:
            return legal_cards[0]
        trick, atout = trick_state, trick_state.atout
        if not trick.plays:
            return self._lead(hand, trick, legal_cards)

        partner = partner_of(self.player_id)
        winning = [c for c in legal_cards if self._hypo_winner(trick, c) == self.player_id]
        if trick_winner(trick.plays, atout) == partner:
            feed = [c for c in legal_cards if c.suit != atout
                    and self._hypo_winner(trick, c) == partner
                    and self._reasonably_safe(hand, trick, c)]
            if feed:
                return max(feed, key=lambda c: (
                    c.points(atout), -self._keep_value(c, hand, atout, trick)))

        if winning:
            safe = [c for c in winning if self._reasonably_safe(hand, trick, c)]
            if (self.is_attacking and len(trick.plays) == 3
                    and not self._opponents_have_trumps(hand, trick)):
                # Rare economy exception: last to play, no enemy trumps remain.
                return min(winning, key=lambda c: (c.points(atout), -self._strength(c, atout)))
            if not safe:
                # Do not cash an ace into a KNOWN impending cut when we can duck.
                voids = self._known_voids(trick)
                later = [(self.player_id + n) % 4 for n in range(1, 4 - len(trick.plays))]
                cut_risk = any(team_of(p) != team_of(self.player_id)
                               and trick.plays[0][1].suit in voids[p]
                               and atout not in voids[p] for p in later)
                losers = [c for c in legal_cards if c not in winning]
                if cut_risk and self._opponents_have_trumps(hand, trick) and losers:
                    return self._discard(hand, trick, losers)
            # Point-first, not bridge-style cheapest winner (in attack AND defence).
            return max(safe or winning, key=lambda c: (c.points(atout), -self._strength(c, atout)))
        return self._discard(hand, trick, legal_cards)
