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
