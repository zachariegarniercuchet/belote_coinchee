"""
Calcul du score d'une donne (sections 7, 9 et 10 des règles officielles),
sans les annonces de la section 8 (Carré / Cent / Cinquante / Tierce), qui ne
sont pas implémentées ici à la demande de l'utilisateur.

La belote/rebelote (section 7) est en revanche gérée, mais de façon
simplifiée : plutôt que d'exiger une annonce verbale « Belote » / « Rebelote »
au moment de jouer les cartes, le bonus est attribué automatiquement à
l'équipe du joueur qui détenait le Roi ET la Dame d'atout en main de départ.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bidding import Contract, CoincheState
from .cards import Card, Rank, Suit, ContractMode, Trump

BELOTE_BONUS = 20
DIX_DE_DER_NORMAL = 10
DIX_DE_DER_CAPOT = 100
CHUTE_BASE = 160


def find_belotes(initial_hands: dict[int, list[Card]], atout: Trump) -> dict[Suit, int]:
    """Paires couleur -> détenteur : aucune en SA, jusqu'à quatre en TA (§11)."""
    if atout is ContractMode.SANS_ATOUT:
        return {}
    suits = tuple(Suit) if atout is ContractMode.TOUT_ATOUT else (atout,)
    return {suit: seat for suit in suits for seat, hand in initial_hands.items()
            if {Rank.ROI, Rank.DAME} <= {c.rank for c in hand if c.suit == suit}}


def belote_points_by_team(belotes: dict[Suit, int]) -> dict[int, int]:
    return {team: BELOTE_BONUS * sum(seat % 2 == team for seat in belotes.values()) for team in (0, 1)}


def find_belote_holder(initial_hands: dict[int, list[Card]], atout: Trump) -> int | None:
    """Retourne le joueur qui avait Roi+Dame d'atout en main au départ, sinon None."""
    holders = list(find_belotes(initial_hands, atout).values())
    return holders[0] if len(holders) == 1 else None


def round_to_nearest_ten(score: int) -> int:
    """Arrondi à la dizaine la plus proche, .5 arrondi vers le haut (10.3)."""
    return int((score + 5) // 10 * 10)


@dataclass
class DonneResult:
    preneur_team: int
    defense_team: int
    raw_points: dict[int, int]          # points de plis par équipe (sans dix de der ni belote)
    dix_de_der_team: int | None
    capot_team: int | None              # équipe ayant remporté les 8 plis, s'il y en a une
    belote_team: int | None
    contract_reached: bool
    score_before_rounding: dict[int, int]
    final_scores: dict[int, int]        # arrondis à la dizaine
    total_points: dict[int, int] | None = None  # plis + dix de der + belote (base de comparaison du contrat)
    belote_points: dict[int, int] | None = None  # Plusieurs paires possibles en TA.

    def __repr__(self) -> str:
        return (f"Résultat: preneurs(équipe {self.preneur_team})="
                f"{self.final_scores[self.preneur_team]}, "
                f"défense(équipe {self.defense_team})={self.final_scores[self.defense_team]}")


def compute_donne_score(
    contract: Contract,
    trick_points: dict[int, int],
    last_trick_winner: int,
    capot_team: int | None,
    belote_team: int | None,
    belote_points: dict[int, int] | None = None,
) -> DonneResult:
    """
    Calcule le score d'une donne terminée, conformément à la section 10.1.

    trick_points: total des points de plis (hors dix de der, hors belote) par équipe.
    last_trick_winner: joueur ayant remporté le dernier pli (pour le dix de der).
    capot_team: équipe ayant remporté les 8 plis, le cas échéant.
    belote_team: équipe détenant la belote, le cas échéant.
    """
    preneur_team = contract.team
    defense_team = 1 - preneur_team
    bonuses = ({t: belote_points.get(t, 0) for t in (0, 1)} if belote_points is not None else
               {t: BELOTE_BONUS if belote_team == t else 0 for t in (0, 1)})
    if contract.suit is ContractMode.SANS_ATOUT:
        bonuses = {0: 0, 1: 0}
    bonus_teams = [t for t in (0, 1) if bonuses[t]]
    belote_team = bonus_teams[0] if len(bonus_teams) == 1 else None

    dix_der_value = DIX_DE_DER_CAPOT if capot_team is not None else DIX_DE_DER_NORMAL
    dix_der_team = capot_team if capot_team is not None else (last_trick_winner % 2)

    def belote_bonus(team: int) -> int:
        return bonuses[team]

    raw_total = {}
    for team in (0, 1):
        total = trick_points.get(team, 0)
        if dix_der_team == team:
            total += dix_der_value
        total += belote_bonus(team)
        raw_total[team] = total

    contract_amount = contract.contract_amount()

    if contract.is_capot:
        contract_reached = capot_team == preneur_team
    else:
        contract_reached = raw_total[preneur_team] >= contract.points

    success = contract_reached and raw_total[preneur_team] > raw_total[defense_team]

    is_coinche = contract.coinche_state != CoincheState.NONE
    multiplier = 1
    if contract.coinche_state == CoincheState.COINCHE:
        multiplier = 2
    elif contract.coinche_state == CoincheState.SURCOINCHE:
        multiplier = 4

    score = {0: 0, 1: 0}

    if success:
        if not is_coinche:
            score[preneur_team] = raw_total[preneur_team] + contract_amount
            score[defense_team] = raw_total[defense_team]
        else:
            preneur_points = raw_total[preneur_team] - belote_bonus(preneur_team)
            defense_points = raw_total[defense_team] - belote_bonus(defense_team)
            score[preneur_team] = (preneur_points + contract_amount) * multiplier + belote_bonus(preneur_team)
            score[defense_team] = defense_points + belote_bonus(defense_team)
    else:
        score[preneur_team] = belote_bonus(preneur_team)  # belote imprenable uniquement
        fail_base = 250 if capot_team == defense_team else CHUTE_BASE
        defense_total = fail_base + contract_amount
        if is_coinche:
            defense_total *= multiplier
        score[defense_team] = defense_total + belote_bonus(defense_team)

    final_scores = {team: round_to_nearest_ten(pts) for team, pts in score.items()}

    return DonneResult(
        preneur_team=preneur_team,
        defense_team=defense_team,
        raw_points=trick_points,
        dix_de_der_team=dix_der_team,
        capot_team=capot_team,
        belote_team=belote_team,
        contract_reached=success,
        score_before_rounding=score,
        final_scores=final_scores,
        total_points=dict(raw_total),
        belote_points=bonuses,
    )
