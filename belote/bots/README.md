# `belote/bots/` — tous les bots vivent ici

| Fichier        | Contenu                                                              |
|----------------|----------------------------------------------------------------------|
| `classic.py`   | `RandomBot`, `HeuristicBot` — baselines sans apprentissage           |
| `spark.py`     | `SparkBot` — enchères calibrées + jeu contract-aware                 |
| `spark_v1.py`  | `SparkBotV1` — version figée à règles et enchères calibrées          |
| `spark_v2.py`  | `SparkBotV2` — simulations de répartitions possibles des cartes      |
| `spark_v3.py`  | `SparkBotV3` — + finales exactes et mondes contraints (le plus fort) |
| `brooklyn.py`  | `BrooklynBot` — règles de David : chasse à l'atout et encaissement des points |
| `brooklyn_v2.py` | `BrooklynBotV2` — enchères de partenariat 80/90, crédits et mémoire des soutiens |
| `brooklyn_v3.py` | `BrooklynBotV3` — estimation des cartes récupérables et retour d'atout au partenaire |
| `brooklyn_v4.py` | `BrooklynBotV4` — enchères v3, gros gagnant à l'atout, petite coupe en attaque, dernier atout gardé après la chasse |
| `registry.py`  | `BOT_REGISTRY` : le catalogue officiel + fabriques                   |
| `contract_modes.py` | Jeu SA/TA sur informations publiques, distinct des anciennes politiques à une couleur |
| `brooklyn_modes.py` | Ouvertures et soutien SA/TA communs aux quatre Brooklyn ; crédits publics non réutilisables |
| `weights/`     | **n'existe pas encore** — créé le jour où un bot a des poids (voir §3) |

Pour la stratégie Brooklyn, les premiers benchmarks et la correction des
notifications du moteur web identifiée pendant ces comparaisons, voir
[`BROOKLYN.md`](BROOKLYN.md). Les replays console/web vérifient les mêmes
décisions pour des distributions et graines identiques.

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
       "label": "MonBot v1",
       "family": "MonBot",  # nom de famille choisi par le créateur
       "version": "v1",
       "author": "Ton nom",
       "theme": "Explorateurs",
       "avatars": ["monbot-tom.png", "monbot-nina.png", "monbot-enzo.png", "monbot-lisa.png"],
       "description": "Simule plusieurs mains adverses pour choisir une carte.",
       "level": 3,  # 1 (faible) → 5 (expert), affiché en ★ dans le lobby
       "names": ["Tom", "Nina", "Enzo", "Lisa"],  # prénoms distincts par siège
           # À table : "Tom MonBot v1", "Nina MonBot v1", etc.
       "factory": lambda seat, name: _mon_bot(seat, name),
   },
   # ...
   def _mon_bot(seat, name):
       from .mon_bot import MonBot
       return MonBot(seat, name=name)
   ```

C'est tout : le bot apparaît **automatiquement** dans le lobby web
(sélecteur par siège vide), dans la CLI et dans `GET /api/bots`.

Conserver l'identifiant API d'une version une fois publiée. Les prénoms,
le nom de famille, la version, l'auteur et la courte description sont définis
par son créateur ici, pas dans le frontend. `get_bot_name` et `create_bot`
utilisent le même nom que le champ public `names` du catalogue. Le sélecteur
montre le nom de version, identique à tous les sièges. Les étoiles indiquent
un niveau estimé, pas un classement mesuré. Les bots historiques sont de Zach ;
l'ancienne entrée `spark` est présentée comme de Belote v0, sans modifier son code.
Les familles actuelles sont West (cowboys, `random`), Bohème (bonnets,
`heuristic`), de Belote (aristos, `spark` et `spark_v1` à `spark_v3`) et
Brooklyn (`brooklyn_v1` à `brooklyn_v4`, auteur David, Miles/Nora/Eli/Maya).
Les noms des personnages de Belote et Brooklyn n'affichent pas de suffixe de version
(« Charles de Belote ») ; le sélecteur et les métadonnées distinguent toujours
les moteurs. Les noms des autres familles restent inchangés.
Déposer les portraits dans `frontend-github-pages/assets/bots/` : ce dossier
est partagé par le frontend statique et la route Flask `/assets/bots/<fichier>`.
Le catalogue expose les quatre noms de fichiers dans `avatars`. La session
accepte aussi quatre valeurs `None` pour une famille sans portraits (Brooklyn
pour le moment) ; le frontend masque alors les images sans emprunter celles
d'une autre famille. La session
transmet `bot_profiles` par siège uniquement pour les joueurs bots ; ne jamais
déduire le type du joueur de son prénom. Les versions d'une même famille
partagent les portraits, mais restent distinguées par leur numéro de version.

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
