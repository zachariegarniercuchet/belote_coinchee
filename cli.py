#!/usr/bin/env python3
"""
Point d'entrée pour jouer à la belote coinchée en console.

Usage:
    python3 cli.py
"""

from __future__ import annotations

import random
import sys

from belote import Game, HeuristicBot
from belote.human_cli import HumanCLIPlayer


def ask_int(prompt: str, default: int, min_v: int, max_v: int) -> int:
    raw = input(f"{prompt} [{default}] : ").strip()
    if not raw:
        return default
    try:
        v = int(raw)
        if min_v <= v <= max_v:
            return v
    except ValueError:
        pass
    print(f"Valeur invalide, on garde {default}.")
    return default


def print_donne_summary(log) -> None:
    print("\n" + "=" * 60)
    print(f"Donneur : joueur {log.dealer}")
    if log.annulee:
        print("Tout le monde a passé : donne annulée, pas de points marqués.")
        return

    print(f"Contrat retenu : {log.contract}")
    print("-" * 60)
    for i, (plays, winner) in enumerate(zip(log.tricks, log.trick_winners), start=1):
        detail = "  ".join(f"J{p}:{c}" for p, c in plays)
        print(f"Pli {i}: {detail}  -> remporté par joueur {winner}")

    r = log.result
    print("-" * 60)
    print(f"Points de plis : équipe 0 = {r.raw_points.get(0, 0)}, équipe 1 = {r.raw_points.get(1, 0)}")
    if r.belote_team is not None:
        print(f"Belote/Rebelote pour l'équipe {r.belote_team} (+20)")
    if r.capot_team is not None:
        print(f"Capot réalisé par l'équipe {r.capot_team} !")
    print(f"Contrat {'réussi' if r.contract_reached else 'chuté'}.")
    print(f"Score de la donne -> équipe 0: {r.final_scores[0]}, équipe 1: {r.final_scores[1]}")


def main() -> None:
    print("=== Belote Coinchée ===\n")
    n_humans = ask_int("Combien de joueurs humains ? (0 à 4)", 1, 0, 4)
    target = ask_int("Score à atteindre pour gagner la partie", 1000, 100, 5000)

    players = {}
    for i in range(4):
        if i < n_humans:
            name = input(f"Nom du joueur humain en position {i} : ").strip() or f"Joueur{i}"
            players[i] = HumanCLIPlayer(i, name)
        else:
            players[i] = HeuristicBot(i, name=f"Bot{i}")

    print("\nPlaces à table (équipe 0 = joueurs 0 et 2, équipe 1 = joueurs 1 et 3) :")
    for i in range(4):
        team = i % 2
        print(f"  Joueur {i} ({players[i].name}) - équipe {team}")

    rng = random.Random()
    game = Game(players, target_score=target, rng=rng)

    donne_num = 0
    while not game.finished:
        donne_num += 1
        print(f"\n\n############ DONNE {donne_num} ############")
        log = game.play_one_donne()
        print_donne_summary(log)
        print(f"\nScore cumulé -> équipe 0: {game.cumulative_scores[0]}, "
              f"équipe 1: {game.cumulative_scores[1]}  (objectif : {target})")

    print("\n" + "#" * 60)
    print(f"FIN DE LA PARTIE ! L'équipe {game.winner_team} remporte la partie "
          f"avec {game.cumulative_scores[game.winner_team]} points.")
    print("#" * 60)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nPartie interrompue.")
        sys.exit(0)
