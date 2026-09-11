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
from .cards import Card, Rank, Suit

BELOTE_BONUS = 20
DIX_DE_DER_NORMAL = 10
DIX_DE_DER_CAPOT = 100
CHUTE_BASE = 160


def find_belote_holder(initial_hands: dict[int, list[Card]], atout: Suit) -> int | None:
    """Retourne le joueur qui avait Roi+Dame d'atout en main au départ, sinon None."""
    for player, hand in initial_hands.items():
        ranks = {c.rank for c in hand if c.suit == atout}
        if Rank.ROI in ranks and Rank.DAME in ranks:
            return player
    return None


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

    dix_der_value = DIX_DE_DER_CAPOT if capot_team is not None else DIX_DE_DER_NORMAL
    dix_der_team = capot_team if capot_team is not None else (last_trick_winner % 2)

    def belote_bonus(team: int) -> int:
        return BELOTE_BONUS if belote_team == team else 0

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
    )
