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
    """80/90 opening, partner support, then one-time distribution bonuses.

    Credits are measured from our TEAM'S last bid, not an intervening enemy
    bid. Opponents cannot manufacture additional hand value by overcalling.
    All accounting is reconstructed from public history, never hidden hands.
    """

    # Initial working convention: +10 for two dix seconds, on rebidding only.
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
    def _opening_value(hand, suit):
        trumps = [c for c in hand if c.suit == suit]
        honours = {c.rank for c in trumps} & {Rank.VALET, Rank.NEUF}
        if len(trumps) < 3 or not honours:
            return None
        return 90 if len(honours) == 2 else 80

    @staticmethod
    def _belote_bonus(hand, suit):
        ranks = {c.rank for c in hand if c.suit == suit}
        return 20 if {Rank.ROI, Rank.DAME} <= ranks else 0

    def _rebid_bonus(self, hand, suit):
        trumps = [c for c in hand if c.suit == suit]
        # Total own credits, including belote already used at the opening.
        # The ceiling calculation subtracts nothing twice or on repeated turns.
        bonus = self._belote_bonus(hand, suit) + 10 * sum(c.rank == Rank.AS for c in hand)
        sides = [[c for c in hand if c.suit == s] for s in Suit if s != suit]
        voids = sum(not cards for cards in sides)
        if voids >= 2 and len(trumps) >= 4:
            bonus += 20  # total void bonus, not 10 + 20
        elif voids and len(trumps) >= 3:
            bonus += 10
        seconds = sum(len(cards) == 2 and any(c.rank == Rank.DIX for c in cards)
                      for cards in sides)
        if seconds >= self.SECOND_TENS_REQUIRED:
            bonus += 10
        return bonus

    @staticmethod
    def _partner_support(hand, suit):
        honours = sum(c.suit == suit and c.rank in (Rank.VALET, Rank.NEUF) for c in hand)
        # Under this convention opener already has at least one J/9.
        missing_honour = min(1, honours)
        aces = sum(c.rank == Rank.AS for c in hand)  # includes the trump ace
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
                candidates = [a for a in numeric if a.suit == suit and a.points <= ceiling]
                if candidates:
                    return max(candidates, key=lambda a: a.points)
            return self._doubles_or_pass(hand, bidding_state, legal_actions)

        openings = []
        for suit in Suit:
            base = self._opening_value(hand, suit)
            if base is None:
                continue
            opening = base + self._belote_bonus(hand, suit)
            candidates = [a for a in numeric if a.suit == suit and a.points == opening]
            if candidates:
                # Describe trumps + belote only. Shape/aces/tens cannot fund an
                # initial overcall: those credits are reserved for a later rebid.
                action = candidates[0]
                trumps = [c for c in hand if c.suit == suit]
                openings.append((base, len(trumps), self._rebid_bonus(hand, suit),
                                 sum(c.points(suit) for c in trumps), action))
        if openings:
            return max(openings, key=lambda entry: entry[:4])[-1]
        return self._doubles_or_pass(hand, bidding_state, legal_actions)
