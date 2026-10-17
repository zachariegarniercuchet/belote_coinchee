# Belote Coinchée — moteur de jeu

Implémentation en Python des règles officielles de la Belote Coinchée
(4 joueurs, 2 équipes), d'après le document *"Règles officielles de la
belote coinchée"* de la Fédération Française de Belote.

## Ce qui est implémenté

- Distribution complète (mélange, coupe, distribution 3-2-3) — §3
- Enchères complètes : passe, enchère chiffrée (multiples de 10, ≥ 80),
  capot, coinche, surcoinche, avec toutes les règles de validité et de fin
  de tour d'enchères — §4
- Jeu de la carte avec **toutes** les règles d'obligation : fournir la
  couleur, couper si on ne peut pas fournir et que le partenaire n'est pas
  maître, monter (surcouper) si un adversaire a déjà coupé, l'exception du
  « ne pas pisser », et le cas où le partenaire est maître donnant liberté
  totale — §5.2
- Ordre et valeur des cartes à l'atout et hors atout — §6
- Belote / Rebelote (bonus de 20 points) — §7
- Dix de der et capot (bonus de 10 ou 100 points sur le dernier pli) — §9
- Calcul complet du score : contrat réussi/chuté, coinche (×2) et
  surcoinche (×4), transformation en 160/250 points en cas de coinche,
  arrondi à la dizaine la plus proche — §10
- Fin de partie au score cible, avec gestion de l'égalité et du cas
  particulier « belote uniquement » qui prolonge la partie — §10.4

## Ce qui n'est **volontairement pas** implémenté (à la demande du projet)

- Les **annonces** (Carré, Cent, Cinquante, Tierce) — §8. Le code est
  structuré pour qu'on puisse les ajouter facilement plus tard (un module
  `announces.py` viendrait s'insérer entre la distribution et le premier
  pli, et ajouterait ses bonus dans `scoring.compute_donne_score`).
- La variante **Sans Atout / Tout Atout** — §11.

## Simplification assumée

La Belote/Rebelote (§7) est normalement soumise à une annonce verbale au
moment de jouer le Roi puis la Dame d'atout. Pour un jeu numérique de
première version, le bonus est ici attribué **automatiquement** à l'équipe
qui détient les deux cartes en main de départ, sans exiger d'annonce
explicite. Facile à changer plus tard si vous voulez la règle stricte.

## Structure du code

```
belote/
    cards.py        # Cartes, couleurs, valeurs, distribution
    bidding.py       # Enchères (BiddingState, Contract, BidAction)
    trick.py         # Cartes jouables (legal_cards) + résolution des plis
    scoring.py       # Calcul du score d'une donne
    player.py        # Interface abstraite Player (pour brancher humains ou IA)
    game.py          # Donne (une main) et Game (partie complète)
    bots/            # TOUS les bots : classic.py, spark*.py, registry.py (+ README.md)
    human_cli.py     # Joueur humain piloté au clavier (console)
cli.py               # Point d'entrée pour jouer en console
tests/
    test_rules.py    # Tests manuels sur les règles délicates et le score
```

## Jouer une partie en console

```bash
python3 cli.py
```

Vous choisissez le nombre de joueurs humains (0 à 4) et le score cible ;
les places manquantes sont comblées par des bots. Les joueurs 0 et 2 sont
en équipe, ainsi que les joueurs 1 et 3.

## Jouer avec l'interface web

Les fichiers de l'interface web sont à la racine du projet : `server.py`,
`extensions.py`, `game_session.py`, `rooms.py`, `serialize.py`, `index.html`,
`app.js` et `style.css`. Le moteur de règles reste dans le dossier `belote/`.

Dans PowerShell, depuis ce dossier :

```powershell
python -m pip install -r requirements.txt
python server.py
```

Ouvrir ensuite `http://localhost:5000` sur l'ordinateur qui lance le serveur.
Pour jouer depuis un téléphone sur le même Wi-Fi, ouvrir l'adresse réseau
affichée par le serveur, par exemple `http://192.168.1.25:5000`.

Pour tester seul, cocher **Compléter les sièges vides avec des bots**, prendre
un siège, puis démarrer la partie. Pour jouer à plusieurs, chaque joueur ouvre
l'adresse du serveur et rejoint le même code de salon. Le terminal doit rester
ouvert pendant la partie.

Pour **observer quatre bots**, créer un salon, s'asseoir uniquement à la place
**Plateau (écran partagé)**, laisser les quatre sièges joueurs libres, garder
**Compléter les sièges vides avec des bots** coché, puis démarrer. Choisir les
bots dans les sélecteurs du salon. Le plateau affiche le jeu et attend un clic
sur le récapitulatif entre les donnes ; en cas de tablage, cliquer d'abord sur
**Voir les scores**.

Si l'environnement `.venv` a déjà été préparé, le lancement local tient en une
commande PowerShell depuis la racine :

```powershell
.\.venv\Scripts\python.exe -B server.py
```

Ouvrir `http://localhost:5000` sur ce PC, ou l'adresse Wi-Fi affichée dans le
terminal depuis l'iPhone connecté au même réseau. Arrêter le serveur avec
`Ctrl+C`. Cette version locale utilise directement les fichiers de la racine,
sans déploiement Render ni copie GitHub Pages.

Le jeu table automatiquement entre deux plis dans deux situations certaines :
une main ne contient plus que des atouts et personne d'autre n'a d'atout,
ou il n'y a plus d'atouts et toutes les cartes du joueur qui entame sont
maîtresses dans leur couleur. Les cartes restantes des quatre joueurs sont
alors révélées côte à côte auprès de leurs noms, et les plis restants sont
attribués avec le dix de der et le capot éventuel. **Voir les scores** permet
ensuite d'ouvrir le récapitulatif. Si un appareil occupe le siège plateau,
c'est sur cet appareil que les mains sont révélées.

Les mains sont triées de la carte la plus forte à la plus faible. Une fois les
enchères terminées, les atouts passent dans l'ordre Valet, 9, As, 10, Roi,
Dame, 8, 7, avec une courte animation. Les groupes de couleurs alternent
rouge/noir autant que possible : pique, cœur, trèfle, carreau à quatre
couleurs, ou un sandwich de teintes à trois couleurs.

## Lancer les tests

```bash
python3 tests/test_rules.py
```

## Utiliser le moteur directement (pour vos futurs algorithmes)

```python
from belote import Game, RandomBot, HeuristicBot

players = {0: HeuristicBot(0), 1: RandomBot(1), 2: HeuristicBot(2), 3: RandomBot(3)}
game = Game(players, target_score=1000)
winner_team = game.play_until_end()
print(game.cumulative_scores)
```

Tous les bots sont centralisés dans le package `belote/bots/`
(`BOT_REGISTRY`, `list_bots()`, `create_bot(bot_id, seat, name)`) : c'est la
seule chose à toucher pour brancher un nouveau bot — voir
`belote/bots/README.md`. Sur le web, chaque siège vide du lobby propose un
sélecteur de bot (catalogue exposé sur `GET /api/bots`), et la CLI propose
aussi le choix du bot.

Pour brancher un algorithme, il suffit d'implémenter la classe abstraite
`belote.player.Player` :

```python
from belote.player import Player

class MonBot(Player):
    def choose_bid(self, hand, bidding_state, legal_actions):
        ...  # doit retourner une action parmi legal_actions

    def choose_card(self, hand, trick_state, legal_cards):
        ...  # doit retourner une carte parmi legal_cards
```

`bidding_state` et `trick_state` exposent tout l'état nécessaire (main des
autres joueurs non incluse, bien sûr) pour construire un algorithme de
décision : historique des enchères, plis déjà joués, atout, etc.

Chaque `DonneLog` (retourné par `Game.play_one_donne()`) contient
l'historique complet d'une main (mains initiales, enchères, plis, score)
si vous voulez générer des données d'entraînement.

## Prochaines étapes envisagées (hors périmètre de cette livraison)

- Algorithmes de jeu plus avancés (règles expertes, recherche, apprentissage).
- Interface conviviale multi-joueurs avec système de « room » rejoignable
  par QR code.
