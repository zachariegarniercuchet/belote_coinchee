"""
Muse Spark bot for Belote Coinchee.

Stronger than HeuristicBot on two axes:
  1. Bidding discipline: hand evaluation calibrated on simulated donnes
     (every level targets ~80%+ success), support for overbids, suit
     changes, coinche and surcoinche — and it never bids capot or above
     120 (measured capot success was ~10%).
  2. Contract-aware card play: draws trumps as declarer, never draws as
     defender, feeds points to a winning partner ("schnellen") while
     ducking cheap against winning opponents, economises honours
     (Valet/Neuf d'atout) on cheap tricks.

Interface: implements belote.player.Player, so it plugs into Game, cli.py
and the web server (game_session.py) like any other bot.
"""

from __future__ import annotations

import random

from ..bidding import ActionType, BidAction, BiddingState
from ..cards import ATOUT_ORDER, ATOUT_POINTS, NONATOUT_ORDER, Card, Rank, Suit, ContractMode
from .contract_modes import choose_mode_card
from ..player import Player
from ..trick import TrickState, partner_of, team_of, trick_winner


class SparkBot(Player):
    """Muse Spark player: disciplined bidding + contract-aware card play."""

    def __init__(self, player_id: int, name: str | None = None,
                 rng: random.Random | None = None):
        super().__init__(player_id, name or f"Spark{player_id}")
        self.rng = rng or random.Random()
        self._reset_donne_state()

    # ------------------------------------------------------------------ #
    # donne memory
    # ------------------------------------------------------------------ #

    def _reset_donne_state(self) -> None:
        self.contract = None
        self.atout = None
        self.is_preneur = False
        self.belote_bonus = 0  # 20 if WE hold K+Q of trump at deal time
        self.played_by_suit: dict[Suit, set[Rank]] = {s: set() for s in Suit}
        self.void_suits: dict[int, set[Suit]] = {p: set() for p in range(4)}
        self.team_points: dict[int, int] = {0: 0, 1: 0}
        self.tricks_played = 0
        self._full_hand: list[Card] | None = None  # snapshot during bidding

    def notify_contract(self, contract) -> None:
        saved = self._full_hand
        self._reset_donne_state()
        self.contract = contract
        self.atout = contract.suit
        self.is_preneur = team_of(self.player_id) == contract.team
        self._full_hand = saved
        if saved is not None:
            ranks = {c.rank for c in saved if c.suit == self.atout}
            if Rank.ROI in ranks and Rank.DAME in ranks:
                self.belote_bonus = 20

    def notify_trick_result(self, plays: list[tuple[int, Card]], winner: int) -> None:
        atout = self.atout
        pts = sum(c.points(atout) for _, c in plays)
        self.team_points[team_of(winner)] += pts
        self.tricks_played += 1
        for _, card in plays:
            self.played_by_suit[card.suit].add(card.rank)
        for player, suit in self._infer_voids(plays):
            self.void_suits[player].add(suit)

    def _infer_voids(self, plays: list[tuple[int, Card]]) -> list[tuple[int, Suit]]:
        atout = self.atout
        suit_led = plays[0][1].suit
        voids: list[tuple[int, Suit]] = []
        for i in range(1, len(plays)):
            player, card = plays[i]
            prior = plays[:i]
            if card.suit != suit_led:
                voids.append((player, suit_led))
            if isinstance(atout, Suit) and suit_led != atout and card.suit != atout:
                atout_prior = [(p, c) for p, c in prior if c.suit == atout]
                if atout_prior:
                    best_is_atout = True
                    best_player = min(atout_prior,
                                      key=lambda pc: pc[1].atout_strength_index())[0]
                else:
                    best_is_atout = False
                    led_prior = [(p, c) for p, c in prior if c.suit == suit_led]
                    best_player = (min(led_prior,
                                        key=lambda pc: pc[1].nonatout_strength_index())[0]
                                   if led_prior else None)
                partner_master = (best_player is not None
                                  and team_of(best_player) == team_of(player))
                if not best_is_atout and not partner_master:
                    voids.append((player, atout))
        return voids

    # ------------------------------------------------------------------ #
    # BIDDING
    # ------------------------------------------------------------------ #

    def _base_strength(self, hand: list[Card], suit: Suit) -> int:
        score = 0
        for c in hand:
            if c.suit == suit:
                score += ATOUT_POINTS[c.rank] + 5
            elif c.rank == Rank.AS:
                score += 3
        return score

    def _evaluate(self, hand: list[Card], suit: Suit) -> tuple[int, dict]:
        """Hand value if `suit` becomes trump. Returns (score, details)."""
        score = self._base_strength(hand, suit)
        trumps = [c for c in hand if c.suit == suit]
        trump_ranks = {c.rank for c in trumps}
        detail = {"trumps": len(trumps)}

        # trump length: long suits make tricks, short suits leak
        if len(trumps) >= 5:
            score += 4
        elif len(trumps) == 4:
            score += 1
        elif len(trumps) <= 2:
            score -= 6

        # key honours
        if Rank.VALET in trump_ranks:
            score += 6
        if Rank.NEUF in trump_ranks and len(trumps) >= 3:
            score += 5
        elif Rank.NEUF in trump_ranks:
            score += 2
        if Rank.AS in trump_ranks:
            score += 2

        # belote (K+Q of trump): 20 bonus points are (almost) guaranteed
        if Rank.ROI in trump_ranks and Rank.DAME in trump_ranks:
            score += 8
            detail["belote"] = True

        # side suits: aces win, guarded 10s win, singletons cut
        for side in Suit:
            if side == suit:
                continue
            cards = [c for c in hand if c.suit == side]
            ranks = {c.rank for c in cards}
            if Rank.AS in ranks:
                score += 7
                if Rank.DIX in ranks:
                    score += 5  # 10 guarded by the Ace is nearly free
                elif len(cards) >= 2:
                    score += 1
            elif Rank.DIX in ranks and len(cards) >= 3:
                score += 3  # long 10 without ace: ~40% to survive
            if len(cards) == 0 and len(trumps) >= 3:
                score += 4  # void: spare trumps cut this suit
            elif len(cards) == 1 and len(trumps) >= 4:
                score += 2  # singleton: cut from 2nd round
        return score, detail

    def _score_to_bid(self, score: int, n_trumps: int) -> int | None:
        """Map evaluation score to a bid level (points) or None.

        Calibrated offline on Spark-team declarers (avg RAW trick points
        by new-scale score, Spark card play):
          65: avg 118, P(>=90)=82%  | 70: avg 120, P(>=100)=75%
          75: avg 121, P(>=100)=79% | 80: avg 130, P(>=110)=76%
          85: avg 135, P(>=110)=91% | 90: avg 141, P(>=120)=83%
        A chute hands the opponents 160+contract, so every level targets
        ~75-80%+ success (breakeven is ~65-70%). Never bid above 120 and
        never capot: measured capot success was ~10%.

        Note there is no 80: with P(>=90) ~= 80%+ at the entry threshold,
        opening 80 is dominated by 90 (same risk, worse payout, and 80
        lets the opponents enter cheaply at 90).
        """
        if n_trumps < 3:
            return None  # short suits cannot reliably make a contract
        if score >= 88:
            return 120
        if score >= 83:
            return 110
        if score >= 77:
            return 100
        if score >= 63:
            return 90
        return None

    def choose_bid(self, hand: list[Card], bidding_state: BiddingState,
                   legal_actions: list[BidAction]) -> BidAction:
        self._full_hand = list(hand)
        if len(legal_actions) == 1:
            return legal_actions[0]
        passe = next(a for a in legal_actions if a.type == ActionType.PASSE)

        # evaluate every suit
        evals = {}
        for suit in Suit:
            score, detail = self._evaluate(hand, suit)
            evals[suit] = (score, detail)
        best_suit = max(evals, key=lambda s: evals[s][0])
        best_score, best_detail = evals[best_suit]
        n_trumps = best_detail["trumps"]

        contract = bidding_state.contract
        me, partner = self.player_id, partner_of(self.player_id)

        def find_bid(suit: Suit, level: int) -> BidAction | None:
            cands = [a for a in legal_actions
                     if a.type == ActionType.ENCHERE and a.suit == suit]
            ok = [a for a in cands if not a.is_capot and a.points == level]
            return ok[0] if ok else None

        # --- no contract yet: open if strong enough -------------------- #
        if contract is None:
            level = self._score_to_bid(best_score, n_trumps)
            if level is None:
                return passe
            action = find_bid(best_suit, level)
            # fall back to a lower legal level if exact level unavailable
            if action is None:
                lower = sorted({a.points for a in legal_actions
                                if a.type == ActionType.ENCHERE and a.suit == best_suit
                                and not a.is_capot and a.points <= level},
                               reverse=True)
                if lower:
                    action = find_bid(best_suit, lower[0])
            return action or passe

        # --- our team holds the contract -------------------------------- #
        if team_of(contract.player) == team_of(me):
            # partner's contract: support it, or speak a strong new suit
            if contract.player == partner and not contract.is_capot:
                cur = contract.comparison_value()
                # (a) change of suit with a self-sufficient hand
                if best_suit != contract.suit and best_score >= 72:
                    lvl = self._score_to_bid(best_score, n_trumps)
                    if lvl is not None:
                        lvl = min(lvl, 110)
                        if lvl > cur:
                            action = find_bid(best_suit, lvl)
                            if action is not None:
                                return action
                # (b) raise partner's suit in support (3+ trumps)
                mine = [c for c in hand if c.suit == contract.suit]
                support = len(mine) + (2 if Rank.VALET in {c.rank for c in mine} else 0)
                if len(mine) >= 3 or support >= 4:
                    want = min(110, ((cur // 10) + 1) * 10)
                    if best_score >= 60:  # partner + support: cheaper to raise
                        cands = [a for a in legal_actions
                                 if a.type == ActionType.ENCHERE and a.suit == contract.suit
                                 and not a.is_capot and a.points is not None
                                 and a.points >= want and a.points <= want + 10]
                        if cands:
                            return min(cands, key=lambda a: a.points)
            # my own contract was overbid by partner in another suit: pass
            # (don't steal). Raising our own bid: only with a monster.
            if contract.player == me and best_score >= 88:
                cur = contract.comparison_value()
                cands = [a for a in legal_actions
                         if a.type == ActionType.ENCHERE and a.suit == best_suit
                         and not a.is_capot and (a.points or 0) > cur
                         and (a.points or 0) <= 120]
                if cands:
                    return min(cands, key=lambda a: a.points or 0)
            # coinched by opponents: surcoinche iff still likely to make
            coinche = next((a for a in legal_actions
                            if a.type == ActionType.SURCOINCHE), None)
            if coinche is not None:
                # contract is ours and coinched: defend it only when solid
                sup, _d = self._evaluate(hand, contract.suit)
                if sup >= 77 or (contract.player == partner and sup >= 72):
                    return coinche
                return passe
            return passe

        # --- opponents hold the contract -------------------------------- #
        # (a) coinche if we can likely beat them
        coinche = next((a for a in legal_actions if a.type == ActionType.COINCHE), None)
        if coinche is not None and not contract.is_capot:
            mine_in_theirs = [c for c in hand if c.suit == contract.suit]
            ranks = {c.rank for c in mine_in_theirs}
            honours = len(ranks & {Rank.VALET, Rank.NEUF, Rank.AS})
            defe, _d = self._evaluate(hand, contract.suit)
            # Coinche only when we hold their suit (their honours are missing
            # so their contract likely falls) AND the contract is not too big
            # to break. A failed coinche doubles their score — be strict.
            if defe >= 62 and (len(mine_in_theirs) >= 3 and honours >= 2):
                if contract.points is not None and contract.points >= 110:
                    pass
                else:
                    return coinche
        # (b) overbid if our hand is strong enough for a higher bid.
        # Winner's curse: the team that wins a bidding war holds the weaker
        # hand consistent with its bid, so overbids need a clear margin and
        # are capped at 110.
        level = self._score_to_bid(best_score, n_trumps)
        if level is not None and best_score >= 63:
            cur = contract.comparison_value()
            level = min(level, 110)
            if level > cur:
                action = find_bid(best_suit, level)
                if action is None:
                    cands = [a for a in legal_actions
                             if a.type == ActionType.ENCHERE and not a.is_capot
                             and (a.points or 0) > cur
                             and (a.points or 0) <= level
                             and (a.suit == best_suit or (a.points or 0) <= level - 10)]
                    if cands:
                        # prefer our best suit
                        same = [a for a in cands if a.suit == best_suit]
                        action = min(same or cands, key=lambda a: a.points or 0)
                if action is not None:
                    return action
        return passe

    # ------------------------------------------------------------------ #
    # CARD PLAY
    # ------------------------------------------------------------------ #

    def _played_ranks(self, suit: Suit, trick_state: TrickState) -> set[Rank]:
        played = set(self.played_by_suit.get(suit, set()))
        for _, c in trick_state.plays:
            if c.suit == suit:
                played.add(c.rank)
        return played

    def _remaining_higher(self, card: Card, atout: Suit, trick_state: TrickState) -> int:
        """How many still-unknown cards beat `card` in its suit."""
        order = ATOUT_ORDER if card.suit == atout else NONATOUT_ORDER
        played = self._played_ranks(card.suit, trick_state)
        idx = order.index(card.rank)
        return sum(1 for r in order[:idx] if r not in played)

    def _is_master(self, card: Card, atout: Suit, trick_state: TrickState) -> bool:
        order = ATOUT_ORDER if card.suit == atout else NONATOUT_ORDER
        remaining = [r for r in order if r not in self._played_ranks(card.suit, trick_state)]
        return bool(remaining) and remaining[0] == card.rank

    def _points_needed(self) -> int:
        """Trick points (incl. belote/dix-der estimates) still needed for OUR
        contract math. Positive => we still need points."""
        if self.contract is None or self.contract.is_capot:
            return 0
        mine = self.team_points[team_of(self.player_id)]
        if team_of(self.player_id) == self.contract.team:
            # preneurs: raw_total (tricks + belote) must reach contract.points.
            # team_points only counts trick points so far; belote (if WE hold
            # K+Q, detected at deal time) and a ~5pt dix-der share are added.
            have = mine + self.belote_bonus
            return (self.contract.points or 0) - have - 5
        return 0

    def _hypo_winner(self, trick_state: TrickState, card: Card) -> int:
        hypo = trick_state.plays + [(trick_state.current_player, card)]
        return trick_winner(hypo, trick_state.atout)

    def _keep_value(self, card: Card, hand: list[Card], atout: Suit,
                    trick_state: TrickState) -> float:
        """How much we want to KEEP this card (higher = don't throw it)."""
        if card.suit == atout:
            order_val = {Rank.VALET: 100, Rank.NEUF: 80, Rank.AS: 50,
                         Rank.DIX: 40, Rank.ROI: 25, Rank.DAME: 25,
                         Rank.HUIT: 5, Rank.SEPT: 5}[card.rank]
            n_trump = sum(1 for c in hand if c.suit == atout)
            if n_trump <= 2:
                order_val += 15  # last trumps are precious
            return order_val
        if card.rank == Rank.AS:
            return 60
        if card.rank == Rank.DIX:
            same = [c for c in hand if c.suit == card.suit]
            if any(c.rank == Rank.AS for c in same):
                return 45  # guarded 10: nearly a trick
            if len(same) >= 3:
                return 25
            return 8  # naked 10: doomed, feed it to partner
        return {Rank.ROI: 12, Rank.DAME: 11, Rank.VALET: 6,
                Rank.NEUF: 3, Rank.HUIT: 2, Rank.SEPT: 2}[card.rank]

    def _choose_lead(self, hand: list[Card], trick_state: TrickState,
                     legal_cards: list[Card], atout: Suit) -> Card:
        my_trumps = [c for c in hand if c.suit == atout]
        n_trump = len(my_trumps)
        played_trump = self._played_ranks(atout, trick_state)
        my_trump_ranks = {c.rank for c in my_trumps}
        outstanding = [r for r in ATOUT_ORDER
                       if r not in played_trump and r not in my_trump_ranks]
        opponents = [p for p in range(4) if team_of(p) != team_of(self.player_id)]
        opp_have_trump = not all(atout in self.void_suits[p] for p in opponents)

        if self.is_preneur:
            # declarer: draw trumps while holding the best remaining one
            if n_trump >= 2 and outstanding and opp_have_trump:
                best_unknown = next(r for r in ATOUT_ORDER if r not in played_trump)
                if best_unknown in my_trump_ranks:
                    cand = next(c for c in my_trumps if c.rank == best_unknown)
                    if cand in legal_cards:
                        return cand
            # else cash side winners: aces first, then guarded 10s/masters
            side_aces = [c for c in legal_cards
                         if c.suit != atout and c.rank == Rank.AS]
            if side_aces:
                # longest suit's ace first (frees the suit)
                return max(side_aces,
                           key=lambda c: sum(1 for h in hand if h.suit == c.suit))
            masters = [c for c in legal_cards
                       if c.suit != atout and self._is_master(c, atout, trick_state)
                       and c.points(atout) >= 3]
            if masters:
                return max(masters, key=lambda c: (c.points(atout),
                                                   sum(1 for h in hand if h.suit == c.suit)))
        else:
            # defender: cash side aces (never lead trump), attack, don't help declarer
            side_aces = [c for c in legal_cards
                         if c.suit != atout and c.rank == Rank.AS]
            if side_aces:
                return max(side_aces,
                           key=lambda c: sum(1 for h in hand if h.suit == c.suit))
            # lead a master 10 (ace already out) in a long suit
            masters = [c for c in legal_cards
                       if c.suit != atout and c.rank == Rank.DIX
                       and self._is_master(c, atout, trick_state)]
            if masters:
                return max(masters,
                           key=lambda c: sum(1 for h in hand if h.suit == c.suit))

        # default: longest side suit, cheap card, protecting naked 10s
        side = [c for c in legal_cards if c.suit != atout]
        pool = side or legal_cards
        by_suit: dict[Suit, list[Card]] = {}
        for c in pool:
            by_suit.setdefault(c.suit, []).append(c)
        for suit in sorted(by_suit, key=lambda s: -sum(1 for h in hand if h.suit == s)):
            non_ten = [c for c in by_suit[suit] if c.rank != Rank.DIX]
            if non_ten:
                return min(non_ten, key=lambda c: (c.points(atout),
                                                  self._remaining_higher(c, atout, trick_state)))
        return min(pool, key=lambda c: c.points(atout))

    def choose_card(self, hand: list[Card], trick_state: TrickState,
                    legal_cards: list[Card]) -> Card:
        if isinstance(trick_state.atout, ContractMode):
            return choose_mode_card(self, hand, trick_state, legal_cards)
        if len(legal_cards) == 1:
            return legal_cards[0]
        atout = trick_state.atout
        me = trick_state.current_player

        if not trick_state.plays:
            return self._choose_lead(hand, trick_state, legal_cards, atout)

        # Who wins right now, and are they with us?
        cur_winner = trick_winner(trick_state.plays, atout)
        partner_winning = team_of(cur_winner) == team_of(me)
        trick_pts_now = sum(c.points(atout) for _, c in trick_state.plays)
        late = self.tricks_played >= 5  # last ~3 tricks: full-send for contract

        winning: list[Card] = []
        partner_still_wins: list[Card] = []
        for c in legal_cards:
            w = self._hypo_winner(trick_state, c)
            if w == me:
                winning.append(c)
            elif team_of(w) == team_of(me):
                partner_still_wins.append(c)

        need = self._points_needed() if self.is_preneur else 0

        # 1. partner winning and stays winning: FEED points (schnellen),
        #    but never waste a trump or a future master.
        if partner_winning and partner_still_wins:
            feed = [c for c in partner_still_wins if c.suit != atout
                    and not self._is_master(c, atout, trick_state)]
            if feed:
                # doomed 10s and loose honours first, trumps never
                return max(feed, key=lambda c: (c.points(atout),
                                                -self._keep_value(c, hand, atout, trick_state)))
            return min(partner_still_wins, key=lambda c: c.points(atout))

        # 2. we can win: decide if it's worth it.
        # Note: if the partner was winning but does NOT stay winning with any
        # of our cards, any play hands the trick to the opponents unless we
        # take it ourselves — so taking is mandatory there, not stealing.
        if winning:
            cheapest = min(winning, key=lambda c: (c.points(atout),
                                                   -self._keep_value(c, hand, atout, trick_state)))
            cost = self._keep_value(cheapest, hand, atout, trick_state)
            prize = trick_pts_now + cheapest.points(atout)
            # Take if: late game, or need points for contract, or trick is rich,
            # or the winning card is cheap to spend.
            if late or (self.is_preneur and need > 0 and prize >= 8) \
                    or prize >= 14 or cost < 30 or len(winning) == len(legal_cards):
                return cheapest
            # else: duck — fall through to economy discard
            if partner_still_wins:
                return min(partner_still_wins, key=lambda c: c.points(atout))

        # 3. cannot win (or ducking): shed the cheapest card, but keep masters
        #    and trumps; naked 10s are ideal discards (doomed anyway).
        non_master = [c for c in legal_cards
                      if not self._is_master(c, atout, trick_state)]
        pool = non_master or legal_cards
        # when opponents take the trick, every point we add goes to them:
        # discard strictly cheapest, tie-break by lowest keep-value.
        return min(pool, key=lambda c: (c.points(atout),
                                        self._keep_value(c, hand, atout, trick_state)))
