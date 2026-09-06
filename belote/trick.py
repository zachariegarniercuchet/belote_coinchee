"""
Le jeu de la carte (section 5 des règles officielles) : détermination des
cartes jouables (5.2) et résolution d'un pli (5.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Card, Suit, ATOUT_ORDER, NONATOUT_ORDER


def team_of(player: int) -> int:
    return player % 2


def partner_of(player: int) -> int:
    return (player + 2) % 4


def trick_winner(plays: list[tuple[int, Card]], atout: Suit) -> int:
    """Retourne le joueur qui remporte le pli (règle 5.1)."""
    suit_led = plays[0][1].suit
    atout_plays = [(p, c) for p, c in plays if c.suit == atout]
    if atout_plays:
        return min(atout_plays, key=lambda pc: pc[1].atout_strength_index())[0]
    suit_led_plays = [(p, c) for p, c in plays if c.suit == suit_led]
    return min(suit_led_plays, key=lambda pc: pc[1].nonatout_strength_index())[0]


def legal_cards(hand: list[Card], plays_so_far: list[tuple[int, Card]],
                 atout: Suit, current_player: int) -> list[Card]:
    """
    Calcule les cartes que `current_player` peut légalement jouer, selon les
    règles 5.2 (1 à 4), y compris la précision sur le fait de « ne pas pisser ».
    """
    if not plays_so_far:
        return list(hand)  # c'est l'entame : carte libre

    suit_led = plays_so_far[0][1].suit
    cards_suit_led = [c for c in hand if c.suit == suit_led]

    # Déterminer qui est actuellement maître du pli et avec quel type de carte.
    atout_plays = [(p, c) for p, c in plays_so_far if c.suit == atout]
    if atout_plays:
        best_player, best_card = min(atout_plays, key=lambda pc: pc[1].atout_strength_index())
        best_is_atout = True
    else:
        suit_led_plays = [(p, c) for p, c in plays_so_far if c.suit == suit_led]
        best_player, best_card = min(suit_led_plays, key=lambda pc: pc[1].nonatout_strength_index())
        best_is_atout = False

    partner_is_master = team_of(best_player) == team_of(current_player)

    if suit_led == atout:
        # La couleur demandée est l'atout lui-même.
        if cards_suit_led:  # on a de l'atout : on doit en fournir
            if partner_is_master:
                return cards_suit_led  # règle 2.1 généralisée : libre choix parmi l'atout
            best_idx = best_card.atout_strength_index()
            stronger = [c for c in cards_suit_led if c.atout_strength_index() < best_idx]
            return stronger if stronger else cards_suit_led  # règle 3
        return list(hand)  # pas d'atout : rien n'oblige, défausse libre

    # La couleur demandée n'est pas l'atout.
    if cards_suit_led:
        return cards_suit_led  # règle 1

    atout_in_hand = [c for c in hand if c.suit == atout]
    if not atout_in_hand:
        return list(hand)  # rien à couper, défausse libre

    if partner_is_master:
        return list(hand)  # règle 2.1 : libre choix (défausse ou coupe)

    if best_is_atout:
        # Un adversaire a déjà coupé : on doit monter si on le peut (règle 3),
        # sinon on n'est pas obligé de "pisser" (précision de la règle 2.2).
        best_idx = best_card.atout_strength_index()
        stronger = [c for c in atout_in_hand if c.atout_strength_index() < best_idx]
        if stronger:
            return stronger
        return list(hand)  # ne pas pisser : défausse libre (y compris avec de l'atout faible)

    # Personne n'a encore coupé : on doit couper avec n'importe quel atout (règle 2.2).
    return atout_in_hand


@dataclass
class TrickState:
    leader: int
    atout: Suit
    plays: list[tuple[int, Card]] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return len(self.plays) == 4

    @property
    def current_player(self) -> int:
        if not self.plays:
            return self.leader
        return (self.plays[-1][0] + 1) % 4

    def legal_cards_for(self, hand: list[Card]) -> list[Card]:
        return legal_cards(hand, self.plays, self.atout, self.current_player)

    def play(self, player: int, card: Card) -> None:
        if player != self.current_player:
            raise ValueError("Ce n'est pas le tour de ce joueur.")
        self.plays.append((player, card))

    def winner(self) -> int:
        if not self.is_complete:
            raise ValueError("Le pli n'est pas terminé.")
        return trick_winner(self.plays, self.atout)

    def points(self) -> int:
        return sum(c.points(self.atout) for _, c in self.plays)
