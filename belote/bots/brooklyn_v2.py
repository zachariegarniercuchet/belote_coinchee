"""Brooklyn card play with David's incremental partnership bidding convention."""

from __future__ import annotations

from dataclasses import dataclass

from ..bidding import ActionType
from ..cards import Rank, Suit
from ..trick import partner_of, team_of
from .brooklyn import BrooklynBot


@dataclass(frozen=True)
class PartnershipRaise:
    history_index: int
    suit: Suit
    from_points: int
    to_points: int

    @property
    def points(self):
        return self.to_points - self.from_points


class BrooklynBotV2(BrooklynBot):
    """Qualified 80/90 base, side aces/belote on entry, then shape credits.

    Credits are measured from our TEAM'S last bid, not an intervening enemy
    bid. Opponents cannot manufacture additional hand value by overcalling.
    All accounting is reconstructed from public history, never hidden hands.
    """

    # Two dix seconds can qualify an opening; their +10 bonus stays at rebid.
    SECOND_TENS_REQUIRED = 2  # dix seconds: ten + exactly one other side-suit card

    def __init__(self, player_id, name=None, rng=None):
        super().__init__(player_id, name, rng)
        self._reset_bidding_memory()

    def _reset_bidding_memory(self):
        self._auction = None
        self.partner_raises: list[PartnershipRaise] = []
        self.partner_raise_points = 0

    def notify_donne_start(self):
        super().notify_donne_start()
        self._reset_bidding_memory()

    @staticmethod
    def _second_tens(hand, suit):
        sides = [[c for c in hand if c.suit == s] for s in Suit if s != suit]
        return sum(len(cards) == 2 and any(c.rank == Rank.DIX for c in cards)
                   for cards in sides)

    @classmethod
    def _opening_value(cls, hand, suit):
        trumps = [c for c in hand if c.suit == suit]
        honours = {c.rank for c in trumps} & {Rank.VALET, Rank.NEUF}
        if len(trumps) < 3 or not honours:
            return None
        if not any(c.rank == Rank.AS and c.suit != suit for c in hand) and \
                cls._second_tens(hand, suit) < cls.SECOND_TENS_REQUIRED:
            return None
        return 90 if len(honours) == 2 else 80

    @staticmethod
    def _belote_bonus(hand, suit):
        ranks = {c.rank for c in hand if c.suit == suit}
        if not {Rank.ROI, Rank.DAME} <= ranks:
            return 0
        return 20 if sum(c.suit == suit for c in hand) >= 4 else 10

    def _entry_bonus(self, hand, suit):
        # Trump ace is already covered by the 80/90 trump description.
        # The first SIDE ace qualifies the base; only additional aces add +10.
        aces = sum(c.rank == Rank.AS and c.suit != suit for c in hand)
        return self._belote_bonus(hand, suit) + 10 * max(0, aces - 1)

    def _rebid_bonus(self, hand, suit):
        trumps = [c for c in hand if c.suit == suit]
        # Total own credits, INCLUDING aces/belote already used on entry.
        bonus = self._entry_bonus(hand, suit)
        sides = [[c for c in hand if c.suit == s] for s in Suit if s != suit]
        voids = sum(not cards for cards in sides)
        if voids >= 2 and len(trumps) >= 4:
            bonus += 20  # total void bonus, not 10 + 20
        elif voids and len(trumps) >= 4:
            bonus += 10
        if self._second_tens(hand, suit) >= self.SECOND_TENS_REQUIRED:
            bonus += 10
        return bonus

    @staticmethod
    def _partner_support(hand, suit):
        honours = sum(c.suit == suit and c.rank in (Rank.VALET, Rank.NEUF) for c in hand)
        # Under this convention opener already has at least one J/9.
        missing_honour = min(1, honours)
        aces = sum(c.rank == Rank.AS and c.suit != suit for c in hand)
        return 10 * (missing_honour + aces)

    def _episode(self, state):
        """Our team's bids in its latest announced suit, ignoring enemy changes."""
        bids = []
        for index, (seat, action) in enumerate(state.history):
            if team_of(seat) != team_of(self.player_id) or action.type != ActionType.ENCHERE:
                continue
            if bids and action.suit != bids[-1][2].suit:
                bids = []
            bids.append((index, seat, action))
        spent = {self.player_id: 0, partner_of(self.player_id): 0}
        self.partner_raises = []
        for previous, current in zip(bids, bids[1:]):
            index, seat, action = current
            before = previous[2]
            if before.points is None or action.points is None:
                continue
            delta = action.points - before.points
            spent[seat] += delta
            if seat == partner_of(self.player_id):
                self.partner_raises.append(PartnershipRaise(index, action.suit, before.points, action.points))
        self.partner_raise_points = sum(raise_.points for raise_ in self.partner_raises)
        # TODO David: use these PUBLIC raise amounts to inform opening a new
        # side suit during play. They do not identify which hidden ace is held;
        # opener's rebids may also include belote/distribution, not just aces.
        return bids, spent

    def _doubles_or_pass(self, hand, state, legal):
        # Keep v1's cautious coinche/surcoinche, without its numeric bids.
        doubles = [a for a in legal if a.type != ActionType.ENCHERE]
        return super().choose_bid(hand, state, doubles)

    def choose_bid(self, hand, bidding_state, legal_actions):
        if self._auction is not bidding_state:
            self._reset_bidding_memory()
            self._auction = bidding_state
        self._full_hand = list(hand)
        bids, spent = self._episode(bidding_state)
        numeric = [a for a in legal_actions if a.type == ActionType.ENCHERE and not a.is_capot]
        choices = []
        team_suit = bids[-1][2].suit if bids else None

        def consider(suit, ceiling):
            candidates = [a for a in numeric if a.suit == suit and a.points <= ceiling]
            if candidates:
                action = max(candidates, key=lambda a: a.points)
                trumps = [c for c in hand if c.suit == suit]
                # Prefer supporting the current suit on equal value; switch
                # only to an independently justified, stronger legal proposal.
                choices.append((action.points, suit == team_suit, len(trumps),
                                sum(c.points(suit) for c in trumps), action))

        if bids:
            _, opener, _ = bids[0]
            latest = bids[-1][2]
            if not latest.is_capot:
                suit = latest.suit
                if opener == self.player_id:
                    base = self._opening_value(hand, suit)
                    ceiling = (base + self._rebid_bonus(hand, suit) + self.partner_raise_points
                               if base is not None else 0)
                else:
                    unused = max(0, self._partner_support(hand, suit) - spent[self.player_id])
                    ceiling = latest.points + unused
                consider(suit, ceiling)

        for suit in Suit:
            if suit == team_suit:
                continue
            base = self._opening_value(hand, suit)
            if base is None:
                continue
            # A new suit starts its own budget: never transfer partner credits
            # from the previous suit, or spend void/tens credits on first entry.
            consider(suit, base + self._entry_bonus(hand, suit))
        if choices:
            return max(choices, key=lambda entry: entry[:4])[-1]
        return self._doubles_or_pass(hand, bidding_state, legal_actions)
