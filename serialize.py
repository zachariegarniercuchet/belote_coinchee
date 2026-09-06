"""Conversion des objets du moteur belote (Card, BidAction...) en dicts JSON-friendly."""

from __future__ import annotations

from belote.cards import Card, Rank, Suit

RED_SUITS = {"COEUR", "CARREAU"}

_RANK_ORDER = {r: i for i, r in enumerate(Rank)}
_SUIT_ORDER = {s: i for i, s in enumerate(Suit)}


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


def sorted_hand(hand):
    return sorted(hand, key=lambda c: (_SUIT_ORDER[c.suit], _RANK_ORDER[c.rank]))


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