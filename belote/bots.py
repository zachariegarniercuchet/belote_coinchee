"""
Bots simples pour pouvoir jouer/tester dès maintenant. Ce ne sont PAS les
algorithmes évolués prévus dans une prochaine étape du projet : juste de quoi
faire tourner une partie complète de bout en bout.
"""

from __future__ import annotations

import random

from .bidding import ActionType, BidAction, BiddingState
from .cards import Card, Suit, ATOUT_POINTS
from .player import Player
from .trick import TrickState


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
    """
    Bot un peu moins naïf : évalue la force de sa main par couleur pour décider
    s'il enchérit, et joue la plus petite carte légale qui gagne le pli si
    possible, sinon la plus petite carte légale (défausse économique).
    """

    def __init__(self, player_id: int, name: str | None = None, rng: random.Random | None = None):
        super().__init__(player_id, name or f"Bot{player_id}")
        self.rng = rng or random.Random()

    def _suit_strength(self, hand: list[Card], suit: Suit) -> int:
        score = 0
        for c in hand:
            if c.suit == suit:
                score += ATOUT_POINTS[c.rank] + 5  # bonus pour la simple longueur à cette couleur
            else:
                score += {  # une carte forte hors-couleur reste un petit atout de points
                    "A": 3,
                }.get(c.rank.value, 0)
        return score

    def choose_bid(self, hand, bidding_state, legal_actions):
        if len(legal_actions) == 1:  # seule "passe" possible
            return legal_actions[0]

        best_suit, best_score = None, -1
        for suit in Suit:
            s = self._suit_strength(hand, suit)
            if s > best_score:
                best_suit, best_score = suit, s

        # Barème arbitraire mais raisonnable pour un bot naïf.
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

    def choose_card(self, hand, trick_state: TrickState, legal_cards: list[Card]):
        atout = trick_state.atout
        if not trick_state.plays:
            # entame : joue une carte moyenne pour ne pas dévoiler ses meilleures cartes
            return sorted(legal_cards, key=lambda c: c.points(atout))[len(legal_cards) // 2]

        # essaie de trouver une carte qui remporterait le pli si posée maintenant
        winning_candidates = []
        for c in legal_cards:
            hypothetical = trick_state.plays + [(trick_state.current_player, c)]
            from .trick import trick_winner
            if trick_winner(hypothetical, atout) == trick_state.current_player:
                winning_candidates.append(c)

        if winning_candidates:
            # gagne le pli avec la carte la moins chère possible
            return min(winning_candidates, key=lambda c: c.points(atout))

        # ne peut pas gagner : se défausse de la carte la moins chère
        return min(legal_cards, key=lambda c: c.points(atout))
