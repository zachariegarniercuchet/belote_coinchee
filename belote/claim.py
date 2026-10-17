"""Deux cas certains de tablage, vérifiés uniquement entre deux plis."""

from dataclasses import dataclass

from .cards import Card, Suit
from .trick import TrickState


@dataclass(frozen=True)
class Claim:
    seat: int
    reason: str  # "trumps" : seuls atouts ; "masters" : toutes les cartes maîtresses


def find_claim(hands: dict[int, list[Card]], leader: int, atout: Suit) -> Claim | None:
    """Trouve un joueur assuré de gagner tous les plis, quel que soit son ordre de jeu.

    Les mains doivent avoir la même taille : ne jamais tabler au milieu d'un pli.
    Le dernier pli se joue automatiquement, sans être présenté comme un tablage.
    Les cartes déjà jouées ne participent pas à la comparaison des forces.
    """
    if set(hands) != {0, 1, 2, 3} or leader not in hands:
        return None
    sizes = {len(hand) for hand in hands.values()}
    if len(sizes) != 1 or len(hands[leader]) < 2:
        return None

    trump_holders = {
        seat for seat, hand in hands.items() if any(card.suit == atout for card in hand)
    }
    if len(trump_holders) == 1:
        seat = next(iter(trump_holders))
        if all(card.suit == atout for card in hands[seat]):
            return Claim(seat, "trumps")

    if trump_holders:
        return None
    others = [card for seat, hand in hands.items() if seat != leader for card in hand]
    if all(
        card.nonatout_strength_index() < other.nonatout_strength_index()
        for card in hands[leader] for other in others if card.suit == other.suit
    ):
        return Claim(leader, "masters")
    return None


def play_claim(hands: dict[int, list[Card]], leader: int, atout: Suit,
               claim: Claim) -> list[TrickState]:
    """Résout les plis réclamés avec des cartes légales, sans modifier les mains.

    Conserve un historique complet pour le score, le dix de der et le capot.
    """
    remaining = {seat: list(hand) for seat, hand in hands.items()}
    tricks = []
    while remaining[leader]:
        trick = TrickState(leader=leader, atout=atout)
        for _ in range(4):
            seat = trick.current_player
            card = trick.legal_cards_for(remaining[seat])[0]
            trick.play(seat, card)
            remaining[seat].remove(card)
        if trick.winner() != claim.seat:
            raise ValueError("Le tablage ne garantit pas tous les plis.")
        tricks.append(trick)
        leader = claim.seat
    return tricks
