"""
Orchestration complète : une Donne (une main, sections 3 à 10) et une Game
(une partie complète jusqu'au score cible, section 10.4).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .bidding import ActionType, BiddingState, Contract
from .cards import Card, Suit, cut_deck, deal, new_shuffled_deck
from .player import Player
from .scoring import DonneResult, compute_donne_score, find_belote_holder, BELOTE_BONUS
from .trick import TrickState, team_of


@dataclass
class DonneLog:
    """Trace complète d'une donne, utile pour l'affichage (CLI) ou le débogage."""
    dealer: int
    initial_hands: dict[int, list[Card]]
    bidding_history: list[tuple[int, object]]
    contract: Contract | None
    annulee: bool
    tricks: list[list[tuple[int, Card]]] = field(default_factory=list)
    trick_winners: list[int] = field(default_factory=list)
    result: DonneResult | None = None


class Donne:
    """Une main complète : distribution, enchères, jeu de la carte, score."""

    def __init__(self, players: dict[int, Player], dealer: int, rng: random.Random | None = None):
        self.players = players
        self.dealer = dealer
        self.rng = rng or random.Random()

    def play(self) -> DonneLog:
        deck = new_shuffled_deck(self.rng)
        deck = cut_deck(deck, self.rng)
        starting_player = (self.dealer - 1) % 4
        hands = deal(deck, starting_player)
        initial_hands = {p: list(h) for p, h in hands.items()}

        bidding_state = BiddingState(dealer=self.dealer)
        while not bidding_state.finished:
            p = bidding_state.current_player
            legal = bidding_state.legal_actions()
            action = self.players[p].choose_bid(hands[p], bidding_state, legal)
            bidding_state.apply(action)

        log = DonneLog(
            dealer=self.dealer,
            initial_hands=initial_hands,
            bidding_history=bidding_state.history,
            contract=bidding_state.contract,
            annulee=bidding_state.annulee,
        )

        if bidding_state.annulee:
            return log

        contract = bidding_state.contract
        for pl in self.players.values():
            pl.notify_contract(contract)
        atout = contract.suit
        leader = (self.dealer - 1) % 4

        trick_points = {0: 0, 1: 0}
        tricks_won_by_team = {0: 0, 1: 0}
        last_trick_winner = leader

        for _ in range(8):
            trick = TrickState(leader=leader, atout=atout)
            for _ in range(4):
                p = trick.current_player
                legal = trick.legal_cards_for(hands[p])
                card = self.players[p].choose_card(hands[p], trick, legal)
                if card not in legal:
                    raise ValueError(f"Le joueur {p} a tenté de jouer une carte illégale: {card}")
                trick.play(p, card)
                hands[p].remove(card)

            winner = trick.winner()
            last_trick_winner = winner
            trick_points[team_of(winner)] += trick.points()
            tricks_won_by_team[team_of(winner)] += 1

            log.tricks.append(list(trick.plays))
            log.trick_winners.append(winner)

            leader = winner
            for pl in self.players.values():
                pl.notify_trick_result(list(trick.plays), winner)

        capot_team = 0 if tricks_won_by_team[0] == 8 else (1 if tricks_won_by_team[1] == 8 else None)
        belote_holder = find_belote_holder(initial_hands, atout)
        belote_team = team_of(belote_holder) if belote_holder is not None else None

        result = compute_donne_score(
            contract=contract,
            trick_points=trick_points,
            last_trick_winner=last_trick_winner,
            capot_team=capot_team,
            belote_team=belote_team,
        )
        log.result = result
        return log


class Game:
    """
    Une partie complète : plusieurs donnes jusqu'à ce qu'une équipe atteigne le
    score cible (10.4), avec gestion du cas d'égalité et du cas particulier de
    la belote (voir note dans _check_end_conditions).
    """

    def __init__(self, players: dict[int, Player], target_score: int = 1000,
                 rng: random.Random | None = None, first_dealer: int | None = None):
        if set(players.keys()) != {0, 1, 2, 3}:
            raise ValueError("Il faut exactement 4 joueurs, identifiés 0, 1, 2 et 3.")
        self.players = players
        self.target_score = target_score
        self.rng = rng or random.Random()
        self.cumulative_scores = {0: 0, 1: 0}
        self.dealer = first_dealer if first_dealer is not None else self.rng.randint(0, 3)
        self.donne_logs: list[DonneLog] = []
        self.finished = False
        self.winner_team: int | None = None

    def play_one_donne(self) -> DonneLog:
        if self.finished:
            raise ValueError("La partie est déjà terminée.")

        donne = Donne(self.players, self.dealer, self.rng)
        log = donne.play()
        self.donne_logs.append(log)

        if not log.annulee:
            for team, pts in log.result.final_scores.items():
                self.cumulative_scores[team] += pts
            self._check_end_conditions(log.result)

        # Le donneur suivant est toujours le voisin de droite, même après une donne annulée.
        self.dealer = (self.dealer - 1) % 4
        return log

    def _check_end_conditions(self, result: DonneResult) -> None:
        over = [t for t in (0, 1) if self.cumulative_scores[t] >= self.target_score]
        if not over:
            return

        # Cas particulier (10.4) : une équipe capot/chute qui ne franchit le score
        # cible que grâce aux 20 points « imprenables » de la belote n'a pas
        # encore gagné : il lui faut un pli supplémentaire pour valider la partie.
        # Simplification : on détecte ce cas quand le seul point marqué par
        # l'équipe sur cette donne provient de la belote (score brut == 20).
        blocked = any(result.score_before_rounding[t] == BELOTE_BONUS for t in over)
        if blocked:
            return  # la partie continue

        if len(over) == 2:
            if self.cumulative_scores[0] == self.cumulative_scores[1]:
                return  # égalité parfaite : la partie continue (une donne de plus)
            self.winner_team = max(over, key=lambda t: self.cumulative_scores[t])
        else:
            self.winner_team = over[0]

        self.finished = True

    def play_until_end(self, max_donnes: int = 500) -> int:
        """Joue des donnes jusqu'à la fin de la partie. Retourne l'équipe gagnante."""
        count = 0
        while not self.finished and count < max_donnes:
            self.play_one_donne()
            count += 1
        if not self.finished:
            raise RuntimeError("La partie ne s'est pas terminée dans la limite de donnes autorisée.")
        return self.winner_team
