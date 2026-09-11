"""
Bots simples pour pouvoir jouer/tester dès maintenant. Ce ne sont PAS les
algorithmes évolués prévus dans une prochaine étape du projet : juste de quoi
faire tourner une partie complète de bout en bout.
"""

from __future__ import annotations

import random

from .bidding import ActionType, BidAction, BiddingState
from .cards import Card, Suit, Rank, ATOUT_POINTS, ATOUT_ORDER, NONATOUT_ORDER
from .player import Player
from .trick import TrickState, trick_winner, team_of, partner_of


class RandomBot(Player):
    """Choisit une action / carte au hasard parmi les options légales."""

    def __init__(self, player_id: int, name: str | None = None, rng: random.Random | None = None):
        super().__init__(player_id, name or f"Bot{player_id}")
        self.rng = rng or random.Random()

    def choose_bid(self, hand, bidding_state, legal_actions):
        # Un peu de bon sens minimal : passer la plupart du temps si on n'a pas d'enchère en cours,
        # pour ne pas transformer chaque donne en enchère au capot au hasard.
        passes = [a for a in legal_actions if a.type == ActionType.PASSE]
        others = [a for a in legal_actions if a.type != ActionType.PASSE]
        if others and self.rng.random() < 0.35:
            # ne jamais choisir un capot au hasard, c'est trop agressif pour un bot naïf
            simple = [a for a in others if not a.is_capot]
            return self.rng.choice(simple or others)
        return self.rng.choice(passes or legal_actions)

    def choose_card(self, hand, trick_state, legal_cards):
        return self.rng.choice(legal_cards)


class HeuristicBot(Player):

    def __init__(self, player_id: int, name: str | None = None, rng: random.Random | None = None):
        super().__init__(player_id, name or f"Bot{player_id}")
        self.rng = rng or random.Random()
        self._reset_donne_state()

    def _reset_donne_state(self) -> None:
        self.contract = None
        self.is_preneur = False
        self.atout = None
        self.played_by_suit: dict[Suit, set[Rank]] = {s: set() for s in Suit}
        self.void_suits: dict[int, set[Suit]] = {p: set() for p in range(4)}

    def notify_contract(self, contract) -> None:
        self._reset_donne_state()
        self.contract = contract
        self.is_preneur = team_of(self.player_id) == contract.team
        self.atout = contract.suit

    def _infer_voids_from_trick(self, plays: list[tuple[int, Card]]) -> list[tuple[int, Suit]]:
        """Rejoue un pli terminé pour en déduire les couleurs (dont l'atout) dont
        certains joueurs sont assurément dépourvus, à partir des seules règles
        d'obligation (fournir / couper), sans connaître leurs mains."""
        atout = self.atout
        suit_led = plays[0][1].suit
        voids = []
        for i in range(1, len(plays)):
            player, card = plays[i]
            prior = plays[:i]
            if card.suit != suit_led:
                voids.append((player, suit_led))
            if suit_led != atout and card.suit != atout:
                atout_prior = [(p, c) for p, c in prior if c.suit == atout]
                if atout_prior:
                    best_is_atout = True
                    best_player = min(atout_prior, key=lambda pc: pc[1].atout_strength_index())[0]
                else:
                    best_is_atout = False
                    suit_led_prior = [(p, c) for p, c in prior if c.suit == suit_led]
                    best_player = (min(suit_led_prior, key=lambda pc: pc[1].nonatout_strength_index())[0]
                                   if suit_led_prior else None)
                partner_master = best_player is not None and team_of(best_player) == team_of(player)
                if not best_is_atout and not partner_master:
                    voids.append((player, atout))  # rule 2.2 : coupe obligatoire si on a de l'atout
        return voids

    def notify_trick_result(self, plays, winner) -> None:
        for _, card in plays:
            self.played_by_suit[card.suit].add(card.rank)
        for player, suit in self._infer_voids_from_trick(plays):
            self.void_suits[player].add(suit)

    # --- helpers ---

    def _suit_strength(self, hand: list[Card], suit: Suit) -> int:
        score = 0
        for c in hand:
            if c.suit == suit:
                score += ATOUT_POINTS[c.rank] + 5
            else:
                score += {"A": 3}.get(c.rank.value, 0)
        return score

    def choose_bid(self, hand, bidding_state, legal_actions):
        if len(legal_actions) == 1:
            return legal_actions[0]

        best_suit, best_score = None, -1
        for suit in Suit:
            s = self._suit_strength(hand, suit)
            if s > best_score:
                best_suit, best_score = suit, s

        candidate_points = 80 if best_score >= 35 else (90 if best_score >= 45 else None)

        non_pass = [a for a in legal_actions if a.type != ActionType.PASSE]
        if candidate_points is None or not non_pass:
            return next(a for a in legal_actions if a.type == ActionType.PASSE)

        matching = [a for a in non_pass
                    if a.type == ActionType.ENCHERE and a.suit == best_suit
                    and not a.is_capot and a.points is not None
                    and a.points <= candidate_points + 10]
        if matching:
            return min(matching, key=lambda a: a.points)

        return next(a for a in legal_actions if a.type == ActionType.PASSE)

    def _played_ranks(self, suit: Suit, trick_state: TrickState) -> set[Rank]:
        played = set(self.played_by_suit.get(suit, set()))
        for _, c in trick_state.plays:
            if c.suit == suit:
                played.add(c.rank)
        return played

    def _is_master(self, card: Card, atout: Suit, trick_state: TrickState) -> bool:
        order = ATOUT_ORDER if card.suit == atout else NONATOUT_ORDER
        remaining = [r for r in order if r not in self._played_ranks(card.suit, trick_state)]
        return bool(remaining) and remaining[0] == card.rank

    def _suit_length(self, hand: list[Card], suit: Suit) -> int:
        return sum(1 for c in hand if c.suit == suit)

    def _trump_clearing_lead(self, hand, trick_state, atout, legal_cards):
        my_trumps = [c for c in hand if c.suit == atout]
        if len(my_trumps) <= 1:
            return None  # on garde toujours son dernier atout

        played = self._played_ranks(atout, trick_state)
        my_ranks = {c.rank for c in my_trumps}
        outstanding = [r for r in ATOUT_ORDER if r not in played and r not in my_ranks]
        if not outstanding:
            return None  # plus d'atout "inconnu" en jeu : chasse terminée

        opponents = [p for p in range(4) if team_of(p) != team_of(self.player_id)]
        if all(atout in self.void_suits[p] for p in opponents):
            return None  # les deux adversaires sont sans atout : le reste est forcément chez le partenaire

        for rank in ATOUT_ORDER:
            if rank in my_ranks and rank not in played:
                candidate = next(c for c in my_trumps if c.rank == rank)
                if candidate in legal_cards:
                    return candidate
        return None

    def _longest_suit_lead(self, hand, legal_cards, atout):
        non_atout_legal = [c for c in legal_cards if c.suit != atout]
        pool = non_atout_legal or legal_cards

        by_suit: dict[Suit, list[Card]] = {}
        for c in pool:
            by_suit.setdefault(c.suit, []).append(c)

        suits_by_length = sorted(by_suit.keys(), key=lambda s: -self._suit_length(hand, s))

        for suit in suits_by_length:
            cheapest = min(by_suit[suit], key=lambda c: c.points(atout))
            if cheapest.rank != Rank.DIX:
                return cheapest
            # la carte la moins chère de cette couleur est un 10 : on essaie une autre couleur

        return min(pool, key=lambda c: c.points(atout))  # tout ce qu'il reste, ce sont des 10

    def _choose_lead(self, hand, trick_state, legal_cards, atout):
        if self.is_preneur:
            trump_lead = self._trump_clearing_lead(hand, trick_state, atout, legal_cards)
            if trump_lead is not None:
                return trump_lead

        master_candidates = [c for c in legal_cards
                              if c.suit != atout and self._is_master(c, atout, trick_state)]
        if master_candidates:
            return max(master_candidates, key=lambda c: self._suit_length(hand, c.suit))

        return self._longest_suit_lead(hand, legal_cards, atout)

    def choose_card(self, hand, trick_state: TrickState, legal_cards: list[Card]):
        atout = trick_state.atout

        if not trick_state.plays:
            return self._choose_lead(hand, trick_state, legal_cards, atout)

        winning_candidates = []
        for c in legal_cards:
            hypothetical = trick_state.plays + [(trick_state.current_player, c)]
            if trick_winner(hypothetical, atout) == trick_state.current_player:
                winning_candidates.append(c)

        if winning_candidates:
            return min(winning_candidates, key=lambda c: c.points(atout))

        return min(legal_cards, key=lambda c: c.points(atout))
