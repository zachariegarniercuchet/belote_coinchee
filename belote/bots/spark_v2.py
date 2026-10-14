"""
Muse Spark bot for Belote Coinchee - VERSION 2.

v2 = v1's bidding + v1's heuristic as the *playout policy*, but card
decisions are taken by a PIMC-lite search:

  1. shortlist candidate cards (v1's pick + up to 3 alternatives),
  2. sample K worlds (consistent with played cards, hand sizes and the
     voids inferred so far),
  3. play out each world to the end of the donne with fast v1 policies,
  4. score each world with the REAL scoring function (trick points so far
     are known exactly; contract bonus / chute / dix-de-der / capot come
     from the simulation; our own belote is known from our initial hand),
  5. play the card with the best mean score differential.

Heuristic micro-tweaks were exhausted first (naive "chasse" LOSES ~90 pts,
void-aware leads ~0, take/duck constant sweeps ~0 — see report_v2.md):
the remaining headroom is in hidden-information search, not in rules.
"""

from __future__ import annotations

import random

from ..bidding import BiddingState, BidAction
from ..cards import Card, Suit, full_deck
from .spark_v1 import SparkBotV1
from ..scoring import compute_donne_score
from ..trick import TrickState, team_of

N_WORLDS = 6
MAX_CANDIDATES = 4


class SparkBotV2(SparkBotV1):
    """Muse Spark player v2: v1 bidding + search-based card play."""

    def __init__(self, player_id: int, name: str | None = None,
                 rng: random.Random | None = None):
        super().__init__(player_id, name or f"SparkV2{player_id}")
        self.rng = rng or random.Random()
        self._past_tricks: list[tuple[list[tuple[int, Card]], int]] = []
        self._own_initial: list[Card] | None = None
        self._bid_id = None

    # ------------------------------------------------------------------ #
    # memory
    # ------------------------------------------------------------------ #

    def notify_contract(self, contract) -> None:
        super().notify_contract(contract)
        self._past_tricks = []

    def notify_trick_result(self, plays: list[tuple[int, Card]], winner: int) -> None:
        super().notify_trick_result(plays, winner)
        self._past_tricks.append((list(plays), winner))

    def choose_bid(self, hand: list[Card], bidding_state: BiddingState,
                   legal_actions: list[BidAction]) -> BidAction:
        if id(bidding_state) != self._bid_id:
            self._bid_id = id(bidding_state)
            self._own_initial = list(hand)
        return super().choose_bid(hand, bidding_state, legal_actions)

    # ------------------------------------------------------------------ #
    # world sampling
    # ------------------------------------------------------------------ #

    def _sample_worlds(self, hand: list[Card], trick_state: TrickState,
                       k: int) -> list[dict[int, list[Card]]]:
        atout = self.atout
        known: set[Card] = set(hand)
        for plays, _w in self._past_tricks:
            for _p, c in plays:
                known.add(c)
        for _p, c in trick_state.plays:
            known.add(c)
        unknown = [c for c in full_deck() if c not in known]

        # current hand sizes of the other seats
        played_count = {p: 0 for p in range(4)}
        for plays, _w in self._past_tricks:
            for p, _c in plays:
                played_count[p] += 1
        for p, _c in trick_state.plays:
            played_count[p] += 1
        sizes = {p: 8 - played_count[p] for p in range(4)}
        sizes[self.player_id] = len(hand)
        assert sum(sizes.values()) == len(unknown) + len(hand), (sizes, len(unknown))

        others = [p for p in range(4) if p != self.player_id]
        voids = self.void_suits
        worlds = []
        rng = self.rng
        for _ in range(k):
            ok = None
            for _try in range(60):
                rng.shuffle(unknown)
                tmp = list(unknown)
                idx = 0
                good = True
                deal: dict[int, list[Card]] = {}
                for p in others:
                    deal[p] = tmp[idx:idx + sizes[p]]
                    idx += sizes[p]
                    if any(c.suit in voids[p] for c in deal[p]):
                        good = False
                        break
                if good:
                    ok = deal
                    break
            if ok is None:
                # relaxation: ignore voids (rare; avoids infinite loops)
                tmp = list(unknown)
                rng.shuffle(tmp)
                idx = 0
                ok = {}
                for p in others:
                    ok[p] = tmp[idx:idx + sizes[p]]
                    idx += sizes[p]
            hands = {self.player_id: list(hand)}
            hands.update({p: list(ok[p]) for p in others})
            worlds.append(hands)
        return worlds

    # ------------------------------------------------------------------ #
    # playout
    # ------------------------------------------------------------------ #

    def _belote_team(self):
        if self._own_initial is not None and self.atout is not None:
            from ..cards import Rank
            ranks = {c.rank for c in self._own_initial if c.suit == self.atout}
            if Rank.ROI in ranks and Rank.DAME in ranks:
                return team_of(self.player_id)
        return None

    def _simulate(self, hands: dict[int, list[Card]], trick_state: TrickState,
                  first_card: Card, shadows: dict[int, SparkBotV1]) -> int:
        """Play first_card then the rest with shadow policies. Returns the
        final score DIFFERENTIAL (our team minus theirs) with real scoring."""
        atout = trick_state.atout
        h = {p: list(hands[p]) for p in hands}
        team_pts = dict(self.team_points)
        tricks_won = {0: 0, 1: 0}
        last_winner = trick_state.leader
        capot: int | None = None

        # finish the current trick with first_card
        cur = TrickState(leader=trick_state.leader, atout=atout,
                         plays=list(trick_state.plays))
        me = cur.current_player
        cur.play(me, first_card)
        h[me].remove(first_card)
        while not cur.is_complete:
            p = cur.current_player
            legal = cur.legal_cards_for(h[p])
            card = shadows[p].choose_card(list(h[p]), cur, list(legal))
            if card not in legal:
                card = legal[0]
            cur.play(p, card)
            h[p].remove(card)
        w = cur.winner()
        last_winner = w
        team_pts[team_of(w)] += cur.points()
        tricks_won[team_of(w)] += 1
        for sh in shadows.values():
            sh.notify_trick_result(list(cur.plays), w)
        leader = w

        remaining = sum(len(h[p]) for p in h) // 4
        for _ in range(remaining):
            cur = TrickState(leader=leader, atout=atout)
            while not cur.is_complete:
                p = cur.current_player
                legal = cur.legal_cards_for(h[p])
                card = shadows[p].choose_card(list(h[p]), cur, list(legal))
                if card not in legal:
                    card = legal[0]
                cur.play(p, card)
                h[p].remove(card)
            w = cur.winner()
            last_winner = w
            team_pts[team_of(w)] += cur.points()
            tricks_won[team_of(w)] += 1
            for sh in shadows.values():
                sh.notify_trick_result(list(cur.plays), w)
            leader = w

        if tricks_won[0] == 8:
            capot = 0
        elif tricks_won[1] == 8:
            capot = 1
        result = compute_donne_score(
            contract=self.contract,
            trick_points={0: team_pts[0], 1: team_pts[1]},
            last_trick_winner=last_winner,
            capot_team=capot,
            belote_team=self._belote_team(),
        )
        # team_pts holds trick points only (no dix-der, no belote yet);
        # compute_donne_score adds those, exactly like the real game.
        ours = team_of(self.player_id)
        return result.final_scores[ours] - result.final_scores[1 - ours]

    # ------------------------------------------------------------------ #
    # decision
    # ------------------------------------------------------------------ #

    def _shortlist(self, hand: list[Card], trick_state: TrickState,
                   legal_cards: list[Card]) -> list[Card]:
        v1pick = super().choose_card(list(hand), trick_state, list(legal_cards))
        if len(legal_cards) <= MAX_CANDIDATES:
            out = [v1pick] + [c for c in legal_cards if c != v1pick]
            return out
        atout = trick_state.atout
        rest = [c for c in legal_cards if c != v1pick]
        rest.sort(key=lambda c: self._keep_value(c, list(hand), atout, trick_state))
        picks = [v1pick]
        if rest:
            picks.append(rest[0])            # cheapest to throw
            if len(rest) > 1:
                picks.append(rest[-1])       # most precious alternative
            if len(rest) > 2:
                picks.append(rest[len(rest) // 2])
        return picks[:MAX_CANDIDATES]

    def choose_card(self, hand: list[Card], trick_state: TrickState,
                    legal_cards: list[Card]) -> Card:
        if len(legal_cards) == 1 or self.contract is None:
            return super().choose_card(list(hand), trick_state, list(legal_cards))
        cands = self._shortlist(list(hand), trick_state, list(legal_cards))
        if len(cands) == 1:
            return cands[0]
        worlds = self._sample_worlds(list(hand), trick_state, N_WORLDS)
        best, best_val = cands[0], None
        for cand in cands:
            total = 0
            for world in worlds:
                # fresh shadows per world (memories diverge during playout)
                sh = {p: SparkBotV1(p) for p in range(4)}
                for s in sh.values():
                    s.notify_contract(self.contract)
                for plays, winner in self._past_tricks:
                    for s in sh.values():
                        s.notify_trick_result(list(plays), winner)
                total += self._simulate(world, trick_state, cand, sh)
            val = total / len(worlds)
            if best_val is None or val > best_val:
                best, best_val = cand, val
        return best
