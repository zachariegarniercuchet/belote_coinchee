#!/usr/bin/env python3
"""
Point d'entrée pour jouer à la belote coinchée en console.

Usage:
    python3 cli.py
"""

from __future__ import annotations

import random
import sys

from belote import Game
from belote.bots import DEFAULT_BOT_ID, create_bot, list_bots
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
    from belote.scoring import BELOTE_BONUS, DIX_DE_DER_CAPOT, DIX_DE_DER_NORMAL
    dix_value = DIX_DE_DER_CAPOT if r.capot_team is not None else DIX_DE_DER_NORMAL
    totals = dict(r.total_points) if getattr(r, "total_points", None) else None
    if totals is None:
        totals = {}
        for team in (0, 1):
            t = r.raw_points.get(team, 0)
            if r.dix_de_der_team == team:
                t += dix_value
            if r.belote_team == team:
                t += BELOTE_BONUS
            totals[team] = t
    for team in (0, 1):
        parts = [f"plis {r.raw_points.get(team, 0)}"]
        if r.dix_de_der_team == team:
            parts.append(f"dix de der +{dix_value}")
        if r.belote_team == team:
            parts.append(f"belote +{BELOTE_BONUS}")
        print(f"Équipe {team} : {' + '.join(parts)} = {totals[team]} pris en compte pour le contrat")
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

    print("\nBots disponibles :")
    for b in list_bots():
        print(f"  {b['id']:>10} : {b['label']} ({'★' * b['level']}{'☆' * (5 - b['level'])}) — par {b['author']}")
        print(f"               {b['description']}")
    bot_id = input(f"Quel bot pour les sièges non humains ? [{DEFAULT_BOT_ID}] : ").strip() or DEFAULT_BOT_ID
    if bot_id not in {b["id"] for b in list_bots()}:
        print(f"Bot inconnu, on garde {DEFAULT_BOT_ID}.")
        bot_id = DEFAULT_BOT_ID

    players = {}
    for i in range(4):
        if i < n_humans:
            name = input(f"Nom du joueur humain en position {i} : ").strip() or f"Joueur{i}"
            players[i] = HumanCLIPlayer(i, name)
        else:
            players[i] = create_bot(bot_id, i)

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
