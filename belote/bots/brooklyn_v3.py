"""Recoverable-card bidding plus explicit partnership support credits."""

from ..cards import ATOUT_ORDER, NONATOUT_ORDER, Rank, Suit
from .brooklyn_v2 import BrooklynBotV2


class BrooklynBotV3(BrooklynBotV2):
    """Value plausible survivors, not face points of cards likely to be lost.

    Confidence weights and opening thresholds are initial heuristics, not a
    guarantee or a fitted probability model. V1/v2 remain frozen baselines.
    """

    # Recoverable-own-point scale, NOT Spark's old strength scale. Partner and
    # captured enemy points are deliberately not assumed on first entry.
    OPENING_THRESHOLDS = ((70, 120), (60, 110), (50, 100), (40, 90), (30, 80))

    @staticmethod
    def _survivors(cards, atout):
        """Pay absent higher honours with weakest cards before crediting wins.

        E.g. side 10/K/Q loses Q to A, retains 10/K; K/Q loses both to A/10.
        Establishment still needs entries and trump control: callers discount
        these prospective winners rather than calling them guaranteed tricks.
        """
        if not cards:
            return [], []
        order = ATOUT_ORDER if cards[0].suit == atout else NONATOUT_ORDER
        held = {c.rank: c for c in cards}
        remaining = dict(held)
        lost = []
        for rank in order:
            if rank in held:
                continue
            weaker = [r for r in remaining if order.index(r) > order.index(rank)]
            if weaker:
                sacrifice = max(weaker, key=order.index)
                lost.append(remaining.pop(sacrifice))
        return list(remaining.values()), lost

    def _recoverable_value(self, hand, suit):
        trumps = [c for c in hand if c.suit == suit]
        ranks = {c.rank for c in trumps}
        jack, nine = Rank.VALET in ranks, Rank.NEUF in ranks
        trump_confidence = .95 if jack and nine else .85 if jack else .75 if nine else .55
        side_confidence = (.9 if jack and nine else .85 if len(trumps) >= 4 and jack
                           else .8 if jack else .75 if nine else .65)
        detail = {"trumps": len(trumps), "suits": {}}
        value = 0.0
        for colour in Suit:
            cards = [c for c in hand if c.suit == colour]
            survivors, lost = self._survivors(cards, suit)
            confidence = trump_confidence if colour == suit else side_confidence
            # Outside trumps, establishing winners after a sacrifice also
            # requires regaining the lead. This is not automatic cashability.
            held = {c.rank for c in cards}
            credited = sum(c.points(suit) * confidence * (
                .7 if colour != suit and any(
                    r not in held for r in NONATOUT_ORDER[:c.nonatout_strength_index()]) else 1
            ) for c in survivors)
            value += credited
            detail["suits"][colour.name] = {
                "survivors": [c.rank.value for c in survivors],
                "sacrifices": [c.rank.value for c in lost],
                "credited_points": round(credited, 2),
            }
        belote = 20 if {Rank.ROI, Rank.DAME} <= ranks else 0
        # Reserve trumps for drawing before assigning any separate cutting
        # capacity. No void bonus at three/four trumps or without the jack.
        spare = max(0, len(trumps) - max(3, 8 - len(trumps))) if jack else 0
        voids = sum(not any(c.suit == s for c in hand) for s in Suit if s != suit)
        cuts = 3 * min(voids, spare)
        detail.update(belote=belote, cut_credit=cuts)
        return round(value + belote + cuts, 2), detail

    def _opening_value(self, hand, suit):
        value, detail = self._recoverable_value(hand, suit)
        if detail["trumps"] < 3:
            return None
        if detail["trumps"] == 3 and not any(
                c.suit == suit and c.rank in (Rank.VALET, Rank.NEUF) for c in hand):
            # Belote alone must not finance an unsupported three-trump opening.
            return None
        return next((bid for threshold, bid in self.OPENING_THRESHOLDS if value >= threshold), None)

    def _entry_bonus(self, hand, suit):
        return 0

    def _rebid_bonus(self, hand, suit):
        return 0

    def _draw_trump(self, hand, trick, legal):
        if (sum(c.suit == trick.atout for c in hand) == 1
                and any(c.suit != trick.atout for c in legal)):
            return None
        return super()._draw_trump(hand, trick, legal)

    @staticmethod
    def _partner_support(hand, suit):
        ranks = {c.rank for c in hand if c.suit == suit}
        # Long trump suits can open without J/9: both may be new information.
        honours = len(ranks & {Rank.VALET, Rank.NEUF})
        aces = sum(c.rank == Rank.AS and c.suit != suit for c in hand)
        belote = 20 if {Rank.ROI, Rank.DAME} <= ranks else 0
        return 10 * (honours + aces) + belote
