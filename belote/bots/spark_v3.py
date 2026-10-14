"""
Muse Spark bot - VERSION 3.

v3 = v2 + three upgrades, each motivated by a measured failure:

1. EXACT ENDGAME per world (double-dummy audit showed 8% error rate in the
   last 3 tricks at ~140 pts a pop for heuristic play). When <=3 tricks
   remain, worlds are solved with exact minimax (alpha-beta + transposition
   table) instead of heuristic playouts. Early donne keeps fast heuristic
   playouts with MORE worlds (12).
2. AUCTION-AWARE world sampling. Bids constrain hands (any 90+ opener holds
   2+ trumps in the suit - proven floor; a support raise or a coinche means
   3+ in the suit - true for every bot in this repo since only v1-family
   ever raises/coinches). Constraints are enforced with graceful fallback.
3. Unchanged, audit-approved v1 bidding (mean margin raw-bid ~+20, every
   level +EV - not too risky).

Dropped after A/B (wash): secured-feed masters rule, void-aware leads,
take/duck constant tweaks, blind chasse.
"""

from __future__ import annotations

import random

from ..bidding import ActionType, BiddingState, BidAction
from ..cards import Card, Suit
from .spark_v1 import SparkBotV1
from .spark_v2 import SparkBotV2
from ..scoring import compute_donne_score
from ..trick import TrickState, team_of, legal_cards as _legal

EXACT_MAX_TRICKS = 3   # <=3 tricks left -> exact minimax per world
N_WORLDS_EARLY = 12
N_WORLDS_LATE = 6


class SparkBotV3(SparkBotV2):
    """Muse Spark player v3: v2 search + exact endgame + auction-aware worlds."""

    def __init__(self, player_id: int, name: str | None = None,
                 rng: random.Random | None = None):
        super().__init__(player_id, name or f"SparkV3{player_id}")
        self.rng = rng or random.Random()
        self._bid_id = None
        # seat -> {suit: min_count} constraints from the auction
        self._auction_min: dict[int, dict[Suit, int]] = {}

    # ------------------------------------------------------------------ #
    # auction memory
    # ------------------------------------------------------------------ #

    def choose_bid(self, hand: list[Card], bidding_state: BiddingState,
                   legal_actions: list[BidAction]) -> BidAction:
        action = super().choose_bid(hand, bidding_state, legal_actions)
        if id(bidding_state) != self._bid_id:
            self._bid_id = id(bidding_state)
            self._auction_min = {}
        for p, act in bidding_state.history:
            if act.type == ActionType.ENCHERE and act.suit is not None \
                    and not act.is_capot:
                cur = self._auction_min.setdefault(p, {})
                cur[act.suit] = max(cur.get(act.suit, 0), 2)
            elif act.type == ActionType.COINCHE:
                c = bidding_state.contract
                if c is not None:
                    cur = self._auction_min.setdefault(p, {})
                    cur[c.suit] = max(cur.get(c.suit, 0), 3)
        # support raises in the contract suit mean 3+ (only v1-family raises;
        # HeuristicBot never raises, so this never misfires against it)
        c = bidding_state.contract
        if c is not None and not c.is_capot:
            for p, act in bidding_state.history:
                if (act.type == ActionType.ENCHERE and act.suit == c.suit
                        and p != c.player and team_of(p) == c.team):
                    cur = self._auction_min.setdefault(p, {})
                    cur[c.suit] = max(cur.get(c.suit, 0), 3)
        return action

    # ------------------------------------------------------------------ #
    # auction-aware sampling (fallback: voids only, then unconstrained)
    # ------------------------------------------------------------------ #

    def _deal_hands(self, unknown: list[Card], others: list[int],
                    sizes: dict[int, int],
                    forbidden: dict[int, set[Suit]]) -> dict[int, list[Card]] | None:
        tmp = list(unknown)
        self.rng.shuffle(tmp)
        idx = 0
        deal: dict[int, list[Card]] = {}
        for p in others:
            deal[p] = tmp[idx:idx + sizes[p]]
            idx += sizes[p]
            if any(c.suit in forbidden.get(p, set()) for c in deal[p]):
                return None
        # auction minimums
        for p in others:
            need = self._auction_min.get(p, {})
            have: dict[Suit, int] = {}
            for c in deal[p]:
                have[c.suit] = have.get(c.suit, 0) + 1
            for s, m in need.items():
                if have.get(s, 0) < m:
                    return None
        return deal

    def _sample_worlds(self, hand: list[Card], trick_state: TrickState,
                       k: int) -> list[dict[int, list[Card]]]:
        known: set[Card] = set(hand)
        for plays, _w in self._past_tricks:
            for _p, c in plays:
                known.add(c)
        for _p, c in trick_state.plays:
            known.add(c)
        from ..cards import full_deck
        unknown = [c for c in full_deck() if c not in known]

        played_count = {p: 0 for p in range(4)}
        for plays, _w in self._past_tricks:
            for p, _c in plays:
                played_count[p] += 1
        for p, _c in trick_state.plays:
            played_count[p] += 1
        sizes = {p: 8 - played_count[p] for p in range(4)}
        sizes[self.player_id] = len(hand)

        others = [p for p in range(4) if p != self.player_id]
        voids = {p: set(s) for p, s in self.void_suits.items()}
        worlds = []
        for _ in range(k):
            deal = None
            for _try in range(80):
                deal = self._deal_hands(unknown, others, sizes, voids)
                if deal is not None:
                    break
            if deal is None:  # fallback 1: drop auction minimums
                saved, self._auction_min = self._auction_min, {}
                try:
                    for _try in range(40):
                        deal = self._deal_hands(unknown, others, sizes, voids)
                        if deal is not None:
                            break
                finally:
                    self._auction_min = saved
            if deal is None:  # fallback 2: unconstrained
                tmp = list(unknown)
                self.rng.shuffle(tmp)
                idx = 0
                deal = {}
                for p in others:
                    deal[p] = tmp[idx:idx + sizes[p]]
                    idx += sizes[p]
            hands = {self.player_id: list(hand)}
            hands.update({p: list(deal[p]) for p in others})
            worlds.append(hands)
        return worlds

    # ------------------------------------------------------------------ #
    # exact minimax (shared transposition table per decision)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tt_key(hands, plays, leader, team_pts, tricks_won, last_winner):
        hk = tuple((p, tuple(sorted((c.suit.name, c.rank.name) for c in hands[p])))
                   for p in range(4))
        pk = tuple((p, c.suit.name, c.rank.name) for p, c in plays)
        return (hk, pk, leader, team_pts[0], team_pts[1],
                tricks_won[0], tricks_won[1], last_winner)

    def _minimax(self, hands: dict[int, list[Card]], plays: list[tuple[int, Card]],
                 leader: int, atout: Suit, team_pts: dict[int, int],
                 tricks_won: dict[int, int], last_winner: int,
                 belote_team, ours: int, tt: dict,
                 alpha: float = -10**9, beta: float = 10**9) -> float:
        if all(len(hands[p]) == 0 for p in range(4)):
            capot = 0 if tricks_won[0] == 8 else (1 if tricks_won[1] == 8 else None)
            r = compute_donne_score(self.contract,
                                    {0: team_pts[0], 1: team_pts[1]},
                                    last_winner, capot, belote_team)
            return r.final_scores[ours] - r.final_scores[1 - ours]
        key = self._tt_key(hands, plays, leader, team_pts, tricks_won, last_winner)
        hit = tt.get(key)
        if hit is not None:
            return hit
        cur_player = leader if not plays else (plays[-1][0] + 1) % 4
        legal = _legal(hands[cur_player], plays, atout, cur_player)
        maximizing = team_of(cur_player) == ours
        ordered = sorted(legal, key=lambda c: c.points(atout), reverse=maximizing)
        best = -10**9 if maximizing else 10**9
        for card in ordered:
            h2 = {p: list(hands[p]) for p in hands}
            h2[cur_player].remove(card)
            plays2 = plays + [(cur_player, card)]
            if len(plays2) == 4:
                w = TrickState(leader=leader, atout=atout, plays=list(plays2)).winner()
                pts2 = dict(team_pts)
                pts2[team_of(w)] += sum(c.points(atout) for _, c in plays2)
                tw2 = dict(tricks_won)
                tw2[team_of(w)] += 1
                val = self._minimax(h2, [], w, atout, pts2, tw2, w,
                                    belote_team, ours, tt, alpha, beta)
            else:
                val = self._minimax(h2, plays2, leader, atout, team_pts,
                                    tricks_won, last_winner,
                                    belote_team, ours, tt, alpha, beta)
            if maximizing:
                if val > best:
                    best = val
                if best >= beta:
                    break
                alpha = max(alpha, best)
            else:
                if val < best:
                    best = val
                if best <= alpha:
                    break
                beta = min(beta, best)
        tt[key] = best
        return best

    def _past_totals(self):
        tw = {0: 0, 1: 0}
        last = None
        for _plays, w in self._past_tricks:
            tw[team_of(w)] += 1
            last = w
        return tw, (last if last is not None else 0)

    def _simulate(self, hands: dict[int, list[Card]], trick_state: TrickState,
                  first_card: Card, shadows: dict, tt: dict | None = None) -> float:
        atout = trick_state.atout
        h = {p: list(hands[p]) for p in hands}
        team_pts = dict(self.team_points)
        tricks_won, last_winner = self._past_totals()
        ours = team_of(self.player_id)
        belote_team = self._belote_team()

        cur = TrickState(leader=trick_state.leader, atout=atout,
                         plays=list(trick_state.plays))
        me = cur.current_player
        cur.play(me, first_card)
        h[me].remove(first_card)

        remaining_tricks = 8 - self.tricks_played  # incl. the current one
        if remaining_tricks <= EXACT_MAX_TRICKS and tt is not None:
            return self._minimax(h, list(cur.plays), cur.leader, atout,
                                 team_pts, tricks_won, last_winner,
                                 belote_team, ours, tt)
        # early donne: fast heuristic playout (v2 behavior)
        return self._heuristic_playout(h, cur, shadows)

    def _heuristic_playout(self, h: dict[int, list[Card]], cur: TrickState,
                           shadows: dict) -> float:
        atout = cur.atout
        team_pts = dict(self.team_points)
        tricks_won, last_winner = self._past_totals()
        # finish current trick
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
        capot = 0 if tricks_won[0] == 8 else (1 if tricks_won[1] == 8 else None)
        result = compute_donne_score(
            contract=self.contract,
            trick_points={0: team_pts[0], 1: team_pts[1]},
            last_trick_winner=last_winner,
            capot_team=capot,
            belote_team=self._belote_team(),
        )
        ours = team_of(self.player_id)
        return result.final_scores[ours] - result.final_scores[1 - ours]

    # ------------------------------------------------------------------ #
    # decision
    # ------------------------------------------------------------------ #

    def choose_card(self, hand: list[Card], trick_state: TrickState,
                    legal_cards: list[Card]) -> Card:
        if len(legal_cards) == 1 or self.contract is None:
            return super().choose_card(list(hand), trick_state, list(legal_cards))
        cands = self._shortlist(list(hand), trick_state, list(legal_cards))
        if len(cands) == 1:
            return cands[0]
        exact_phase = (8 - self.tricks_played) <= EXACT_MAX_TRICKS
        k = N_WORLDS_LATE if exact_phase else N_WORLDS_EARLY
        worlds = self._sample_worlds(list(hand), trick_state, k)
        tt: dict = {}  # shared transposition table for this decision
        best, best_val = cands[0], None
        for cand in cands:
            total = 0.0
            for world in worlds:
                sh = {p: SparkBotV1(p) for p in range(4)}
                for s in sh.values():
                    s.notify_contract(self.contract)
                for plays, winner in self._past_tricks:
                    for s in sh.values():
                        s.notify_trick_result(list(plays), winner)
                total += self._simulate(world, trick_state, cand, sh, tt if exact_phase else None)
            val = total / len(worlds)
            if best_val is None or val > best_val:
                best, best_val = cand, val
        return best
