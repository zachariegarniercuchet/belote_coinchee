"""
Interface abstraite d'un joueur. Toute IA (bot) ou joueur humain doit
implémenter cette interface. C'est le point d'extension pensé pour
brancher plus tard des algorithmes (minimax, MCTS, apprentissage...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .bidding import BidAction, BiddingState, Contract
from .cards import Card, Rank, Suit
from .trick import TrickState, team_of


class Player(ABC):
    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.contract: Contract | None = None
        self._reset_public_information()

    def _reset_public_information(self) -> None:
        self.public_belotes: dict[Suit, int] = {}
        self.known_cards: dict[int, set[Card]] = {p: set() for p in range(4)}
        self.belote_events: list[tuple[int, Card]] = []

    def known_card_owner(self, card: Card) -> int | None:
        return next((seat for seat, cards in self.known_cards.items() if card in cards), None)

    def notify_belote(self, seat: int, card: Card) -> None:
        """Only an actual public announcement reveals the unplayed K/Q mate."""
        if card.rank not in (Rank.ROI, Rank.DAME):
            raise ValueError("Une belote accompagne un roi ou une dame.")
        if (seat, card) in self.belote_events:
            return
        self.belote_events.append((seat, card))
        self.known_cards[seat].discard(card)
        if card.suit not in self.public_belotes:
            mate = Rank.DAME if card.rank is Rank.ROI else Rank.ROI
            self.known_cards[seat].add(Card(mate, card.suit))
        self.public_belotes[card.suit] = seat

    @property
    def is_attacking(self) -> bool:
        """Role in the accepted contract; neither role applies before acceptance."""
        return self.contract is not None and self.contract.team == team_of(self.player_id)

    @property
    def is_defending(self) -> bool:
        return self.contract is not None and self.contract.team != team_of(self.player_id)

    def notify_donne_start(self) -> None:
        """Forget the previous contract before new bidding, even if all pass."""
        self.contract = None
        self._reset_public_information()

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

    def notify_contract(self, contract: Contract) -> None:
        """Point d'extension optionnel : informe le joueur du contrat retenu,
        juste avant le début du jeu de la carte (permet à un bot de savoir s'il
        est preneur et de réinitialiser sa mémoire de donne).
        Une surcharge doit conserver `self.contract` (ou appeler super()).
        Le contrat provisoire pendant les enchères est dans `bidding_state`.
        """
        self.contract = contract
        self._reset_public_information()

    def notify_trick_result(self, plays: list[tuple[int, Card]], winner: int) -> None:
        """Point d'extension optionnel : informe le joueur du résultat d'un pli
        terminé (les 4 cartes jouées et le vainqueur), pour lui permettre de
        mémoriser les cartes sorties."""
        for seat, card in plays:
            self.known_cards[seat].discard(card)
