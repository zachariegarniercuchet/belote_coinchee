"""Conversion des objets du moteur belote (Card, BidAction...) en dicts JSON-friendly."""

from __future__ import annotations

from itertools import permutations

from belote.cards import Card, Suit, Trump

RED_SUITS = {"COEUR", "CARREAU"}

_DISPLAY_SUITS = (Suit.PIQUE, Suit.COEUR, Suit.TREFLE, Suit.CARREAU)


def card_id(card: Card) -> str:
    return f"{card.rank.name}_{card.suit.name}"


def card_to_dict(card: Card) -> dict:
    return {
        "id": card_id(card),
        "rank": card.rank.value,
        "suit": card.suit.name,
        "symbol": card.suit.symbol(),
        "color": "red" if card.suit.name in RED_SUITS else "black",
    }


def card_from_id(cid: str, pool):
    for c in pool:
        if card_id(c) == cid:
            return c
    return None


def sorted_hand(hand: list[Card], atout: Trump | None = None,
                previous_suits: list[Suit] | None = None) -> list[Card]:
    """Trie pour l'affichage : couleurs alternées et cartes les plus fortes d'abord.

    Les égalités d'alternance suivent l'ordre de référence pique/cœur/trèfle/carreau.
    À deux couleurs ou moins, conserver leur ordre d'affichage précédent.
    Le moteur garde sa main d'origine et ses listes d'actions légales inchangées.
    """
    present = [suit for suit in _DISPLAY_SUITS if any(card.suit == suit for card in hand)]
    if len(present) <= 2 and previous_suits:
        suit_order = [suit for suit in previous_suits if suit in present]
        suit_order += [suit for suit in present if suit not in suit_order]
    else:
        suit_order = max(
            permutations(present),
            key=lambda suits: sum(
                (left.name in RED_SUITS) != (right.name in RED_SUITS)
                for left, right in zip(suits, suits[1:])
            ),
        )
    suit_indices = {suit: index for index, suit in enumerate(suit_order)}
    return sorted(hand, key=lambda card: (
        suit_indices[card.suit],
        card.strength_index(atout),
    ))


def bid_action_to_dict(action, index: int) -> dict:
    return {
        "index": index,
        "label": repr(action),
        "type": action.type.name,
        "points": action.points,
        "suit": action.suit.name if action.suit else None,
        "symbol": action.suit.symbol() if action.suit else None,
        "is_capot": action.is_capot,
    }
