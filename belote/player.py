"""
Interface abstraite d'un joueur. Toute IA (bot) ou joueur humain doit
implémenter cette interface. C'est le point d'extension pensé pour
brancher plus tard des algorithmes (minimax, MCTS, apprentissage...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .bidding import BidAction, BiddingState
from .cards import Card
from .trick import TrickState


class Player(ABC):
    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name

    @abstractmethod
    def choose_bid(self, hand: list[Card], bidding_state: BiddingState,
                    legal_actions: list[BidAction]) -> BidAction:
        """Doit retourner une action présente dans legal_actions."""
        raise NotImplementedError

    @abstractmethod
    def choose_card(self, hand: list[Card], trick_state: TrickState,
                     legal_cards: list[Card]) -> Card:
        """Doit retourner une carte présente dans legal_cards."""
        raise NotImplementedError

    def notify(self, message: str) -> None:
        """Point d'extension optionnel pour informer le joueur d'un événement (log, UI...)."""
        pass

    def notify_contract(self, contract) -> None:
        """Point d'extension optionnel : informe le joueur du contrat retenu,
        juste avant le début du jeu de la carte (permet à un bot de savoir s'il
        est preneur et de réinitialiser sa mémoire de donne)."""
        pass

    def notify_trick_result(self, plays: list[tuple[int, Card]], winner: int) -> None:
        """Point d'extension optionnel : informe le joueur du résultat d'un pli
        terminé (les 4 cartes jouées et le vainqueur), pour lui permettre de
        mémoriser les cartes sorties."""
        pass
