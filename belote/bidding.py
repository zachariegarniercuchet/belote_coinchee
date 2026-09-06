"""
Les enchères (section 4 des règles officielles), hors variante Sans Atout /
Tout Atout et sans gestion des annonces (qui sont indépendantes des enchères
de toute façon).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from .cards import Suit

MIN_BID = 80
CAPOT_VALUE_FOR_COMPARISON = 10_000  # le capot est plus fort que toute enchère chiffrée


class ActionType(Enum):
    PASSE = auto()
    ENCHERE = auto()
    COINCHE = auto()
    SURCOINCHE = auto()


@dataclass(frozen=True)
class BidAction:
    type: ActionType
    points: int | None = None          # None si capot, sinon multiple de 10 >= 80
    suit: Suit | None = None
    is_capot: bool = False

    @staticmethod
    def passe() -> "BidAction":
        return BidAction(ActionType.PASSE)

    @staticmethod
    def enchere(points: int, suit: Suit) -> "BidAction":
        return BidAction(ActionType.ENCHERE, points=points, suit=suit, is_capot=False)

    @staticmethod
    def capot(suit: Suit) -> "BidAction":
        return BidAction(ActionType.ENCHERE, points=None, suit=suit, is_capot=True)

    @staticmethod
    def coinche() -> "BidAction":
        return BidAction(ActionType.COINCHE)

    @staticmethod
    def surcoinche() -> "BidAction":
        return BidAction(ActionType.SURCOINCHE)

    def comparison_value(self) -> int:
        return CAPOT_VALUE_FOR_COMPARISON if self.is_capot else (self.points or 0)

    def __repr__(self) -> str:
        if self.type == ActionType.PASSE:
            return "Passe"
        if self.type == ActionType.COINCHE:
            return "Coinché"
        if self.type == ActionType.SURCOINCHE:
            return "Surcoinché"
        val = "Capot" if self.is_capot else str(self.points)
        return f"{val} {self.suit.symbol()}"


class CoincheState(Enum):
    NONE = auto()
    COINCHE = auto()
    SURCOINCHE = auto()


@dataclass
class Contract:
    """Une enchère (chiffrée ou capot) en cours, avec son éventuel état de coinche."""
    player: int
    team: int
    points: int | None
    suit: Suit
    is_capot: bool
    coinche_state: CoincheState = CoincheState.NONE
    coinche_by_team: int | None = None

    def contract_amount(self) -> int:
        """Le « montant du contrat demandé » utilisé dans le calcul du score (10.1)."""
        return 250 if self.is_capot else self.points

    def comparison_value(self) -> int:
        return CAPOT_VALUE_FOR_COMPARISON if self.is_capot else (self.points or 0)

    def __repr__(self) -> str:
        base = "Capot" if self.is_capot else str(self.points)
        s = f"{base} {self.suit.symbol()} (joueur {self.player})"
        if self.coinche_state == CoincheState.COINCHE:
            s += " - Coinché"
        elif self.coinche_state == CoincheState.SURCOINCHE:
            s += " - Surcoinché"
        return s


@dataclass
class BiddingState:
    dealer: int
    num_players: int = 4
    current_player: int = field(init=False)
    contract: Contract | None = None
    passes_in_a_row: int = 0
    history: list[tuple[int, BidAction]] = field(default_factory=list)
    finished: bool = False
    annulee: bool = False  # tous ont passé sans enchère

    def __post_init__(self):
        self.current_player = (self.dealer - 1) % self.num_players  # voisin de droite du donneur

    def team_of(self, player: int) -> int:
        return player % 2

    def legal_actions(self) -> list[BidAction]:
        if self.finished:
            return []
        p = self.current_player
        actions: list[BidAction] = [BidAction.passe()]

        if self.contract is None:
            for suit in Suit:
                for pts in range(MIN_BID, 181, 10):
                    actions.append(BidAction.enchere(pts, suit))
                actions.append(BidAction.capot(suit))
            return actions

        c = self.contract
        if c.coinche_state == CoincheState.NONE:
            if self.team_of(p) == c.team:
                # son propre camp : ne peut que surenchérir ou passer
                for suit in Suit:
                    for pts in range(MIN_BID, 181, 10):
                        if pts > c.comparison_value():
                            actions.append(BidAction.enchere(pts, suit))
                    if not c.is_capot:
                        actions.append(BidAction.capot(suit))
            else:
                for suit in Suit:
                    for pts in range(MIN_BID, 181, 10):
                        if pts > c.comparison_value():
                            actions.append(BidAction.enchere(pts, suit))
                    if not c.is_capot:
                        actions.append(BidAction.capot(suit))
                actions.append(BidAction.coinche())
        elif c.coinche_state == CoincheState.COINCHE:
            if self.team_of(p) == c.team:
                actions.append(BidAction.surcoinche())
            # l'équipe qui a coinché ne peut plus que passer
        # SURCOINCHE : les enchères sont déjà terminées, ne devrait pas arriver ici

        return actions

    def apply(self, action: BidAction) -> None:
        if self.finished:
            raise ValueError("Le tour d'enchères est terminé.")
        if action not in self.legal_actions():
            raise ValueError(f"Action illégale: {action}")

        p = self.current_player
        self.history.append((p, action))

        if action.type == ActionType.PASSE:
            self.passes_in_a_row += 1
            if self.contract is None and self.passes_in_a_row == self.num_players:
                self.finished = True
                self.annulee = True
                return
            if self.contract is not None and self.passes_in_a_row == 3:
                self.finished = True
                return
        elif action.type == ActionType.ENCHERE:
            self.contract = Contract(
                player=p,
                team=self.team_of(p),
                points=action.points,
                suit=action.suit,
                is_capot=action.is_capot,
            )
            self.passes_in_a_row = 0
        elif action.type == ActionType.COINCHE:
            self.contract.coinche_state = CoincheState.COINCHE
            self.contract.coinche_by_team = self.team_of(p)
            self.passes_in_a_row = 0
        elif action.type == ActionType.SURCOINCHE:
            self.contract.coinche_state = CoincheState.SURCOINCHE
            self.finished = True
            return

        self.current_player = (self.current_player + 1) % self.num_players
