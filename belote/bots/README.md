# `belote/bots/` — tous les bots vivent ici

| Fichier        | Contenu                                                              |
|----------------|----------------------------------------------------------------------|
| `classic.py`   | `RandomBot`, `HeuristicBot` — baselines sans apprentissage           |
| `spark.py`     | `SparkBot` — enchères calibrées + jeu contract-aware                 |
| `spark_v1.py`  | `SparkBotV1` — + Monte-Carlo sur mondes possibles                    |
| `spark_v2.py`  | `SparkBotV2` — + échantillonnage des mondes amélioré                 |
| `spark_v3.py`  | `SparkBotV3` — + finales exactes et mondes contraints (le plus fort) |
| `registry.py`  | `BOT_REGISTRY` : le catalogue officiel + fabriques                   |
| `weights/`     | **n'existe pas encore** — créé le jour où un bot a des poids (voir §3) |

Règle d'or : le moteur (`belote/cards.py`, `game.py`, …) ne sait rien des
bots. Tout accès aux bots (serveur web, CLI, futurs tournois) passe par le
registre : `from belote.bots import list_bots, create_bot`.

## 1. Brancher un bot 100 % code (cas courant)

1. **Crée ton fichier** `belote/bots/mon_bot.py` :
   ```python
   from belote.player import Player

   class MonBot(Player):
       def choose_bid(self, hand, bidding_state, legal_actions):
           ...  # doit retourner une action parmi legal_actions

       def choose_card(self, hand, trick_state, legal_cards):
           ...  # doit retourner une carte parmi legal_cards
   ```

2. **Enregistre-le** dans `belote/bots/registry.py` (une entrée, import
   paresseux obligatoire) :
   ```python
   "mon_bot": {
       "label": "MonBot — Expérimental",
       "description": "Monte-Carlo maison.",
       "level": 3,  # 1 (faible) → 5 (expert), affiché en ★ dans le lobby
       "factory": lambda seat, name: _mon_bot(seat, name),
   },
   # ...
   def _mon_bot(seat, name):
       from .mon_bot import MonBot
       return MonBot(seat, name=name)
   ```

C'est tout : le bot apparaît **automatiquement** dans le lobby web
(sélecteur par siège vide), dans la CLI et dans `GET /api/bots`.

## 2. Compétition entre bots (à venir, non implémenté)

Le registre est déjà l'interface dont un futur script de tournoi aura
besoin, sans rien changer au code existant :
```python
from belote import Game
from belote.bots import BOT_REGISTRY, create_bot

players = {seat: create_bot(bot_id, seat) for seat, bot_id in ...}
game = Game(players, target_score=1000)
```
Chaque `DonneLog` contient l'historique complet (mains, enchères, plis,
scores) — de quoi classer les bots et/ou générer des données d'entraînement.

## 3. Bot avec modèle appris (poids lourds) — `weights/`

Le jour où un bot a besoin de fichiers de poids (`*.pt`, `*.onnx`…) :

1. **Crée `belote/bots/weights/`** et dépose-les dedans, ex.
   `belote/bots/weights/mon_modele.pt`. Ils sont déjà ignorés par git
   (voir `.gitignore` à la racine) : chacun les dépose en local sans
   polluer le dépôt. Versionne uniquement les petits fichiers
   (config, tokenizer…).
2. **Charge-les dans ton bot** (`belote/bots/mon_bot.py`) :
   ```python
   import os
   from belote.player import Player

   _WEIGHTS = os.path.join(os.path.dirname(__file__), "weights", "mon_modele.pt")

   class MonBot(Player):
       def __init__(self, player_id, name=None):
           super().__init__(player_id, name or f"MonBot{player_id}")
           self.model = charger_mon_modele(_WEIGHTS)  # ton code ici
       ...
   ```
   Charge les poids **dans `__init__`** (ou en paresseux au premier appel),
   jamais à l'import du module : le serveur doit démarrer même si torch/onnx
   n'est pas installé pour les autres bots. Protège l'import lourd :
   ```python
   try:
       import torch
   except ImportError:
       torch = None
   ```
3. **Enregistre-le** comme au §1.

Pourquoi `weights/` et pas `models/` ? `models/` est ambigu (modèles de
données ? templates ?) ; `weights/` dit exactement ce qu'il contient et
c'est le terme standard en ML (PyTorch, Hugging Face parlent de "weights").
