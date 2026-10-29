"""
Cartes, couleurs et valeurs pour la belote coinchée (32 cartes).

Ce module ne connaît rien des règles de jeu : il définit uniquement les
objets de base (Suit, Rank, Card) et les tables d'ordre/valeur des cartes,
à l'atout et hors atout (section 6 des règles officielles).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
import random


class Suit(Enum):
    PIQUE = "Pique"
    COEUR = "Coeur"
    CARREAU = "Carreau"
    TREFLE = "Trefle"

    def symbol(self) -> str:
        return {
            Suit.PIQUE: "♠",
            Suit.COEUR: "♥",
            Suit.CARREAU: "♦",
            Suit.TREFLE: "♣",
        }[self]


class Rank(Enum):
    SEPT = "7"
    HUIT = "8"
    NEUF = "9"
    DIX = "10"
    VALET = "V"
    DAME = "D"
    ROI = "R"
    AS = "A"


class ContractMode(Enum):
    """Contrats sans couleur d'atout unique ; jamais des couleurs du paquet."""
    SANS_ATOUT = "Sans Atout"
    TOUT_ATOUT = "Tout Atout"

    def symbol(self) -> str:
        return "SA" if self is ContractMode.SANS_ATOUT else "TA"


Trump = Suit | ContractMode
CONTRACT_SUITS = (*Suit, *ContractMode)


# Ordre décroissant de force (index 0 = carte la plus forte) et valeur en points.
ATOUT_ORDER = [Rank.VALET, Rank.NEUF, Rank.AS, Rank.DIX, Rank.ROI, Rank.DAME, Rank.HUIT, Rank.SEPT]
ATOUT_POINTS = {Rank.VALET: 20, Rank.NEUF: 14, Rank.AS: 11, Rank.DIX: 10,
                Rank.ROI: 4, Rank.DAME: 3, Rank.HUIT: 0, Rank.SEPT: 0}

NONATOUT_ORDER = [Rank.AS, Rank.DIX, Rank.ROI, Rank.DAME, Rank.VALET, Rank.NEUF, Rank.HUIT, Rank.SEPT]
NONATOUT_POINTS = {Rank.AS: 11, Rank.DIX: 10, Rank.ROI: 4, Rank.DAME: 3,
                   Rank.VALET: 2, Rank.NEUF: 0, Rank.HUIT: 0, Rank.SEPT: 0}
SANS_ATOUT_POINTS = {**NONATOUT_POINTS, Rank.AS: 19}
TOUT_ATOUT_POINTS = {Rank.VALET: 13, Rank.NEUF: 9, Rank.AS: 6, Rank.DIX: 5,
                     Rank.ROI: 3, Rank.DAME: 2, Rank.HUIT: 0, Rank.SEPT: 0}

TOTAL_POINTS_SANS_DIX_DE_DER = 152  # 90 (3 couleurs non-atout) + 62 (atout)


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __repr__(self) -> str:
        return f"{self.rank.value}{self.suit.symbol()}"

    def points(self, atout: Trump) -> int:
        """Valeur en points de la carte, selon qu'elle est atout ou non."""
        if atout is ContractMode.SANS_ATOUT:
            return SANS_ATOUT_POINTS[self.rank]
        if atout is ContractMode.TOUT_ATOUT:
            return TOUT_ATOUT_POINTS[self.rank]
        if self.suit == atout:
            return ATOUT_POINTS[self.rank]
        return NONATOUT_POINTS[self.rank]

    def strength_index(self, atout: Trump | None) -> int:
        """Force dans sa propre couleur ; ne détermine pas le droit de couper."""
        if atout is ContractMode.TOUT_ATOUT or self.suit == atout:
            return self.atout_strength_index()
        return self.nonatout_strength_index()

    def atout_strength_index(self) -> int:
        """Plus petit index = carte d'atout plus forte. À n'utiliser que sur une carte d'atout."""
        return ATOUT_ORDER.index(self.rank)

    def nonatout_strength_index(self) -> int:
        """Plus petit index = carte plus forte dans sa couleur (hors atout)."""
        return NONATOUT_ORDER.index(self.rank)


def full_deck() -> list[Card]:
    return [Card(rank, suit) for suit, rank in product(Suit, Rank)]


def new_shuffled_deck(rng: random.Random | None = None) -> list[Card]:
    rng = rng or random
    deck = full_deck()
    rng.shuffle(deck)
    return deck


def cut_deck(deck: list[Card], rng: random.Random | None = None) -> list[Card]:
    """La coupe (3.3) : coupe franche en 2, chaque tas ayant au moins 3 cartes."""
    rng = rng or random
    cut_point = rng.randint(3, len(deck) - 3)
    return deck[cut_point:] + deck[:cut_point]


def deal(deck: list[Card], starting_player: int, num_players: int = 4) -> dict[int, list[Card]]:
    """
    Distribution 3-2-3 (3.4), en commençant par le voisin de droite du donneur,
    dans le sens inverse des aiguilles d'une montre (index croissant, modulo).
    """
    hands: dict[int, list[Card]] = {p: [] for p in range(num_players)}
    order = [(starting_player + i) % num_players for i in range(num_players)]
    packet_sizes = [3, 2, 3]
    idx = 0
    for size in packet_sizes:
        for p in order:
            for _ in range(size):
                hands[p].append(deck[idx])
                idx += 1
    return hands
