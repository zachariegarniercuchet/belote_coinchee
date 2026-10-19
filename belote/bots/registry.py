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
    label       : nom de la version dans le sélecteur ("de Belote v3")
    family      : nom de famille choisi par le créateur ("de Belote")
    theme       : identité visuelle de la famille ("Aristos")
    avatars     : 4 fichiers de portraits, associés aux mêmes sièges que names
    version     : version publique ("v3")
    author      : auteur du bot
    description : une ligne pour l'utilisateur
    level       : 1 (faible) → 5 (expert), affiché sous forme d'étoiles
    names       : 4 prénoms distincts (index = siège). Le nom à table combine
                  prénom, famille et version : "Charles de Belote v3".
    factory     : callable (seat, name) -> Player. Import paresseux à
                  l'intérieur de la factory pour ne pas charger torch/onnx
                  (et les futurs gros modèles) au démarrage du serveur.
"""

from __future__ import annotations

from typing import Callable

from ..player import Player

Factory = Callable[[int, str], Player]

DEFAULT_BOT_ID = "spark_v3"

_WEST_PORTRAITS = ["west-buck.png", "west-daisy.png", "west-hank.png", "west-bonnie.png"]
_BOHEME_PORTRAITS = ["boheme-basile.png", "boheme-alma.png", "boheme-marceau.png", "boheme-suzon.png"]
_BELOTE_PORTRAITS = ["belote-charles.png", "belote-alienor.png", "belote-octave.png", "belote-apolline.png"]

BOT_REGISTRY: dict[str, dict] = {
    "random": {
        "label": "West v1",
        "family": "West",
        "theme": "Cowboys",
        "avatars": _WEST_PORTRAITS,
        "version": "v1",
        "author": "Zach",
        "description": "Choisit ses cartes au hasard parmi les coups légaux et passe le plus souvent aux enchères.",
        "level": 1,
        "names": ["Buck", "Daisy", "Hank", "Bonnie"],
        "factory": lambda seat, name: _random_bot(seat, name),
    },
    "heuristic": {
        "label": "Bohème v1",
        "family": "Bohème",
        "theme": "Bobos",
        "avatars": _BOHEME_PORTRAITS,
        "version": "v1",
        "author": "Zach",
        "description": "Suit des règles écrites à la main : enchères prudentes et suivi des cartes déjà jouées.",
        "level": 2,
        "names": ["Basile", "Alma", "Marceau", "Suzon"],
        "factory": lambda seat, name: _heuristic_bot(seat, name),
    },
    "spark": {
        "label": "de Belote v0",
        "family": "de Belote",
        "theme": "Aristos",
        "avatars": _BELOTE_PORTRAITS,
        "version": "v0",
        "author": "Zach",
        "description": "Version originale : enchères calibrées et règles de jeu adaptées au contrat et au partenaire.",
        "level": 3,
        "names": ["Charles", "Aliénor", "Octave", "Apolline"],
        "factory": lambda seat, name: _spark_bot(seat, name),
    },
    "spark_v1": {
        "label": "de Belote v1",
        "family": "de Belote",
        "theme": "Aristos",
        "avatars": _BELOTE_PORTRAITS,
        "version": "v1",
        "author": "Zach",
        "description": "Version figée à règles : évalue sa main aux enchères et adapte ses cartes à l'attaque ou à la défense.",
        "level": 4,
        "names": ["Charles", "Aliénor", "Octave", "Apolline"],
        "factory": lambda seat, name: _spark_bot_v1(seat, name),
    },
    "spark_v2": {
        "label": "de Belote v2",
        "family": "de Belote",
        "theme": "Aristos",
        "avatars": _BELOTE_PORTRAITS,
        "version": "v2",
        "author": "Zach",
        "description": "Simule plusieurs répartitions possibles des cartes cachées et choisit le coup au meilleur score moyen.",
        "level": 4,
        "names": ["Charles", "Aliénor", "Octave", "Apolline"],
        "factory": lambda seat, name: _spark_bot_v2(seat, name),
    },
    "spark_v3": {
        "label": "de Belote v3",
        "family": "de Belote",
        "theme": "Aristos",
        "avatars": _BELOTE_PORTRAITS,
        "version": "v3",
        "author": "Zach",
        "description": "Affine les simulations avec les enchères et calcule exactement les trois derniers plis dans chaque répartition simulée.",
        "level": 5,
        "names": ["Charles", "Aliénor", "Octave", "Apolline"],
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
            "family": entry["family"], "version": entry["version"], "author": entry["author"],
            "theme": entry["theme"], "avatars": list(entry["avatars"]),
            "description": entry["description"], "level": entry["level"],
            "names": [get_bot_name(bot_id, seat) for seat in range(4)]}


def get_bot_name(bot_id: str, seat: int) -> str:
    """Nom public du bot `bot_id` au siège `seat` (prénom, famille, version).

    Déterministe : un même bot au même siège porte toujours le même nom.
    `bot_id` inconnu → repli sur le bot par défaut.
    """
    if bot_id not in BOT_REGISTRY:
        bot_id = DEFAULT_BOT_ID
    entry = BOT_REGISTRY[bot_id]
    first_name = entry["names"][seat % len(entry["names"])]
    return f"{first_name} {entry['family']} {entry['version']}"


def list_bots() -> list[dict]:
    """Liste JSON-safe des bots, pour l'API HTTP et le front web."""
    return [get_bot_info(bot_id) for bot_id in BOT_REGISTRY]


def create_bot(bot_id: str, seat: int, name: str | None = None) -> Player:
    """Instancie le bot `bot_id` pour le siège `seat`.

    `bot_id` inconnu → repli silencieux sur DEFAULT_BOT_ID (une partie web ne
    doit jamais planter à cause d'un vieil id stocké en room).
    Sans `name` explicite, le bot prend son nom public (`get_bot_name`).
    """
    if bot_id not in BOT_REGISTRY:
        bot_id = DEFAULT_BOT_ID
    entry = BOT_REGISTRY[bot_id]
    return entry["factory"](seat, name or get_bot_name(bot_id, seat))
