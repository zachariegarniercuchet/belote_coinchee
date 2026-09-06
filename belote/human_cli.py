"""
Un joueur humain qui joue via la console (input()/print()).
"""

from __future__ import annotations

from .bidding import ActionType, BidAction, BiddingState
from .cards import Card, Suit
from .player import Player
from .trick import TrickState


def format_hand(hand: list[Card]) -> str:
    by_suit: dict[Suit, list[Card]] = {}
    for c in hand:
        by_suit.setdefault(c.suit, []).append(c)
    parts = []
    for suit, cards in by_suit.items():
        parts.append(f"{suit.symbol()}: " + " ".join(str(c) for c in sorted(
            cards, key=lambda c: c.nonatout_strength_index())))
    return "   |   ".join(parts)


def ask_index(prompt: str, n: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 0 <= int(raw) < n:
            return int(raw)
        print(f"  -> entrez un nombre entre 0 et {n - 1}.")


class HumanCLIPlayer(Player):
    def choose_bid(self, hand: list[Card], bidding_state: BiddingState,
                    legal_actions: list[BidAction]) -> BidAction:
        print(f"\n--- Ton tour d'enchère (joueur {self.player_id} - {self.name}) ---")
        print("Ta main :", format_hand(hand))
        if bidding_state.contract is not None:
            print("Enchère actuelle :", bidding_state.contract)
        else:
            print("Aucune enchère pour l'instant.")

        # Pour ne pas noyer l'utilisateur sous 100+ options, on regroupe intelligemment.
        passes = [a for a in legal_actions if a.type == ActionType.PASSE]
        coinches = [a for a in legal_actions if a.type in (ActionType.COINCHE, ActionType.SURCOINCHE)]
        enchere_actions = [a for a in legal_actions if a.type == ActionType.ENCHERE]

        options: list[BidAction] = list(passes) + list(coinches)
        print("Actions disponibles :")
        for i, a in enumerate(options):
            print(f"  [{i}] {a}")
        if enchere_actions:
            print(f"  [{len(options)}] Enchérir (choisir points + couleur)")

        choice = ask_index("Ton choix : ", len(options) + (1 if enchere_actions else 0))
        if choice < len(options):
            return options[choice]

        # Sous-menu enchère : choisir la couleur puis le nombre de points (ou capot).
        suits = sorted({a.suit for a in enchere_actions}, key=lambda s: s.value)
        print("Couleur :")
        for i, s in enumerate(suits):
            print(f"  [{i}] {s.symbol()} {s.value}")
        suit = suits[ask_index("Couleur choisie : ", len(suits))]

        possible_for_suit = sorted(
            [a for a in enchere_actions if a.suit == suit],
            key=lambda a: a.comparison_value(),
        )
        print("Valeur du contrat :")
        for i, a in enumerate(possible_for_suit):
            label = "Capot" if a.is_capot else str(a.points)
            print(f"  [{i}] {label}")
        picked = possible_for_suit[ask_index("Ton choix : ", len(possible_for_suit))]
        return picked

    def choose_card(self, hand: list[Card], trick_state: TrickState, legal_cards: list[Card]) -> Card:
        print(f"\n--- Ton tour de jeu (joueur {self.player_id} - {self.name}) ---")
        print(f"Atout : {trick_state.atout.symbol()}")
        if trick_state.plays:
            print("Pli en cours :", "  ".join(f"J{p}:{c}" for p, c in trick_state.plays))
        else:
            print("C'est toi qui entames ce pli.")
        print("Ta main :", format_hand(hand))
        print("Cartes jouables :")
        for i, c in enumerate(legal_cards):
            print(f"  [{i}] {c}")
        choice = ask_index("Carte à jouer : ", len(legal_cards))
        return legal_cards[choice]
