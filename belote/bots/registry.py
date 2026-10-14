"""
Registre central des bots — unique point d'entrée pour brancher une IA.

Philosophie :
- Le moteur (`belote/`) ne connaît les bots que via ce registre.
- Le serveur web (`server.py`, `game_session.py`), la CLI (`cli.py`) et les
  futurs scripts de compétition listent / instancient les bots d'ici, jamais
  en important directement `bots.py` ou `spark_bot_v*.py`.
- Pour brancher un nouveau bot : UNE entrée dans `BOT_REGISTRY` (ci-dessous)
  + éventuellement un nouveau fichier `belote/bots/<mon_bot>.py`.
  Voir `belote/bots/README.md` (les futurs poids ML iront dans
  `belote/bots/weights/`, créé à la demande).

Chaque entrée contient :
    id          : identifiant stable (clé API, stocké en room, envoyé au front)
    label       : nom affiché dans l'interface ("Spark v3 — Expert")
    description : une ligne pour l'utilisateur
    level       : 1 (faible) → 5 (expert), affiché sous forme d'étoiles
    factory     : callable (seat, name) -> Player. Import paresseux à
                  l'intérieur de la factory pour ne pas charger torch/onnx
                  (et les futurs gros modèles) au démarrage du serveur.
"""

from __future__ import annotations

from typing import Callable

from ..player import Player

Factory = Callable[[int, str], Player]

DEFAULT_BOT_ID = "spark_v3"

BOT_REGISTRY: dict[str, dict] = {
    "random": {
        "label": "Aléatoire",
        "description": "Joue au hasard — utile pour déboguer, très faible.",
        "level": 1,
        "factory": lambda seat, name: _random_bot(seat, name),
    },
    "heuristic": {
        "label": "Heuristique",
        "description": "Règles expertes simples (enchères prudentes, chasse d'atout).",
        "level": 2,
        "factory": lambda seat, name: _heuristic_bot(seat, name),
    },
    "spark": {
        "label": "Spark",
        "description": "Enchères calibrées + jeu contract-aware. Solide.",
        "level": 3,
        "factory": lambda seat, name: _spark_bot(seat, name),
    },
    "spark_v1": {
        "label": "Spark v1",
        "description": "Spark + Monte-Carlo sur mondes possibles (jeu de la carte).",
        "level": 4,
        "factory": lambda seat, name: _spark_bot_v1(seat, name),
    },
    "spark_v2": {
        "label": "Spark v2",
        "description": "v1 + échantillonnage des mondes amélioré.",
        "level": 4,
        "factory": lambda seat, name: _spark_bot_v2(seat, name),
    },
    "spark_v3": {
        "label": "Spark v3 — Expert",
        "description": "v2 + finales exactes (minimax) et mondes contraints par les enchères. Le plus fort.",
        "level": 5,
        "factory": lambda seat, name: _spark_bot_v3(seat, name),
    },
}


# --- factories à import paresseux (pas de dépendance lourde au boot) --------

def _random_bot(seat: int, name: str) -> Player:
    from .classic import RandomBot
    return RandomBot(seat, name=name)


def _heuristic_bot(seat: int, name: str) -> Player:
    from .classic import HeuristicBot
    return HeuristicBot(seat, name=name)


def _spark_bot(seat: int, name: str) -> Player:
    from .spark import SparkBot
    return SparkBot(seat, name=name)


def _spark_bot_v1(seat: int, name: str) -> Player:
    from .spark_v1 import SparkBotV1
    return SparkBotV1(seat, name=name)


def _spark_bot_v2(seat: int, name: str) -> Player:
    from .spark_v2 import SparkBotV2
    return SparkBotV2(seat, name=name)


def _spark_bot_v3(seat: int, name: str) -> Player:
    from .spark_v3 import SparkBotV3
    return SparkBotV3(seat, name=name)


# --- API publique ------------------------------------------------------------

def is_valid_bot(bot_id: str) -> bool:
    return bot_id in BOT_REGISTRY


def get_bot_info(bot_id: str) -> dict:
    entry = BOT_REGISTRY[bot_id]  # lève KeyError si inconnu : volontaire
    return {"id": bot_id, "label": entry["label"],
            "description": entry["description"], "level": entry["level"]}


def list_bots() -> list[dict]:
    """Liste JSON-safe des bots, pour l'API HTTP et le front web."""
    return [get_bot_info(bot_id) for bot_id in BOT_REGISTRY]


def create_bot(bot_id: str, seat: int, name: str | None = None) -> Player:
    """Instancie le bot `bot_id` pour le siège `seat`.

    `bot_id` inconnu → repli silencieux sur DEFAULT_BOT_ID (une partie web ne
    doit jamais planter à cause d'un vieil id stocké en room).
    """
    if bot_id not in BOT_REGISTRY:
        bot_id = DEFAULT_BOT_ID
    entry = BOT_REGISTRY[bot_id]
    return entry["factory"](seat, name or f"{entry['label']} ({seat})")
