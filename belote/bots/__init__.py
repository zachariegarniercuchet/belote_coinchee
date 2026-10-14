"""Tous les bots vivent ici — et nulle part ailleurs.

- `classic.py` : RandomBot, HeuristicBot (baselines sans apprentissage).
- `spark*.py` : famille Spark (v1 → v3, force croissante).
- `registry.py` : catalogue officiel (BOT_REGISTRY) + fabriques. C'est par ici
  que le serveur, la CLI et les futurs tournois accèdent aux bots.
- `README.md` : guide de branchement (nouveau bot, futurs poids `weights/`).

Règle d'or : un nouveau bot = un nouveau module dans ce dossier + UNE entrée
dans `registry.py`. Le moteur (`belote/cards.py`, `game.py`, …) ne sait rien
des bots ; les bots ne se connaissent qu'entre eux via ce package.
"""

from .classic import HeuristicBot, RandomBot
from .registry import (
    BOT_REGISTRY,
    DEFAULT_BOT_ID,
    create_bot,
    get_bot_info,
    is_valid_bot,
    list_bots,
)
from .spark import SparkBot
from .spark_v1 import SparkBotV1
from .spark_v2 import SparkBotV2
from .spark_v3 import SparkBotV3

__all__ = [
    "RandomBot", "HeuristicBot",
    "SparkBot", "SparkBotV1", "SparkBotV2", "SparkBotV3",
    "BOT_REGISTRY", "DEFAULT_BOT_ID", "create_bot", "get_bot_info",
    "is_valid_bot", "list_bots",
]
