# Belote Coinchée — moteur de jeu

Implémentation en Python des règles officielles de la Belote Coinchée
(4 joueurs, 2 équipes), d'après le document *"Règles officielles de la
belote coinchée"* de la Fédération Française de Belote.

## Gate de publication

Chaque push qui modifie une référence demande une confirmation explicite du
commit dans un terminal interactif. Il peut déclencher un redéploiement Render,
qui redémarre le serveur et perd les parties stockées en mémoire. Entrée vide,
confirmation incorrecte ou commande non interactive : **push refusé**.

Activation locale (déjà faite dans le clone de travail actuel) :

```powershell
git config --local core.hooksPath .githooks
```

Les hooks Git ne s'activent pas automatiquement dans un nouveau clone.
Vérifier les hooks existants avant cette configuration pour conserver leurs
contrôles. Cette gate est un garde-fou local, pas une protection GitHub contre
un contournement volontaire. Ne pas la désactiver ni utiliser `--no-verify`.
Un assistant doit en plus demander un feu vert **juste avant chaque push** ;
une demande antérieure ou une validation du code ne vaut pas accord permanent.

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

L'interface web affiche néanmoins automatiquement **« Belote ! »** puis
**« Rebelote ! »** dans une bulle près du joueur lorsqu'il pose les deux cartes
de sa paire roi–dame d'atout, dans un ordre ou dans l'autre. Ces bulles
accompagnent le jeu ; elles ne changent pas le calcul du bonus de 20 points.

## Structure du code

```
belote/
    cards.py        # Cartes, couleurs, valeurs, distribution
    bidding.py       # Enchères (BiddingState, Contract, BidAction)
    trick.py         # Cartes jouables (legal_cards) + résolution des plis
    claim.py         # Détection du tablage et résolution des plis restants
    scoring.py       # Calcul du score d'une donne
    player.py        # Interface abstraite Player (pour brancher humains ou IA)
    game.py          # Donne (une main) et Game (partie complète)
    bots/            # TOUS les bots : classic.py, spark*.py, registry.py (+ README.md)
    human_cli.py     # Joueur humain piloté au clavier (console)
cli.py               # Point d'entrée pour jouer en console
logo/                # Emblème du 10 de trèfle : originaux + icônes dérivées
tests/
    test_rules.py       # Tests manuels sur les règles délicates et le score
    test_autoplay.py    # Dernière carte jouée automatiquement sur le web
    test_claim.py       # Tablage : ordres légaux, scores, mains non révélées
    test_hand_order.py  # Tri des mains et passage à l'ordre d'atout
    test_lobby.py       # Parcours Socket.IO : sièges, bots, reconnexion
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

À la fin d'une donne, **Voir les mains de départ** affiche les quatre mains
initiales autour d'un carré, couleur par couleur et triées selon le contrat.
Le joueur reste en bas. Le sélecteur permet de revoir les donnes terminées
de cette partie, y compris depuis le bilan final ; **Retour aux scores**
ferme cette vue sans continuer la partie. Aucune main inachevée n'est révélée.
Cocher **Revoir les plis, carte par carte** permet de parcourir la donne avec
**Précédent / Suivant** ou le curseur : les mains se vident au fil des cartes
jouées, le pli reste au centre et son gagnant est indiqué. Les fins tablées
sont signalées, car leurs derniers plis sont résolus automatiquement.

Les enchères proposent aussi **SA (Sans Atout)** et **TA (Tout Atout)**,
selon la section 11 de `REGLES-DE-LA-BELOTE-COINCHEE.pdf` :
aucune coupe dans les deux modes ; en TA, monter dans la couleur demandée
est obligatoire, même sur le partenaire. En SA : ordre A–10–R–D–V–9–8–7,
as à 19 points, aucune belote. En TA : ordre V–9–A–10–R–D–8–7,
valeurs 13–9–6–5–3–2–0–0, jusqu'à quatre belotes (20 points par paire).
Les deux modes totalisent 152 points de cartes, puis le dix de der habituel.
Les montants proposés vont jusqu'à 160 en SA, 180 à une couleur et 240 en
TA (belotes comprises), puis Capot ; coinche et surcoinche restent possibles.
Chaque belote TA est révélée séparément à sa première carte annoncée.
Les autres annonces (tierce, cinquante, cent, carré) restent hors périmètre.

Si l'environnement `.venv` a déjà été préparé, double-cliquer sur
**`start-server.cmd`**, ou lancer cette commande PowerShell depuis la racine :

```powershell
.\start-server.cmd
```

Ouvrir `http://localhost:5000` sur ce PC, ou l'adresse Wi-Fi affichée dans le
terminal depuis l'iPhone connecté au même réseau. Arrêter le serveur avec
`Ctrl+C`. Cette version locale utilise directement les fichiers de la racine,
sans déploiement Render ni copie GitHub Pages.
Le lanceur fonctionne sans assistant et ne télécharge rien. Il utilise le
dossier du script, même si on le lance depuis un autre répertoire. La première
installation des dépendances nécessite Internet ; les comptes et certaines
ressources web peuvent aussi nécessiter une connexion pour jouer.

### Comptes optionnels

On peut jouer **en invité, sans compte**, comme avant : c'est le comportement
par défaut et il ne dépend de rien. Si les variables `SUPABASE_URL` et
`SUPABASE_ANON_KEY` sont renseignées (Render ou PowerShell local), un bandeau
**Invité · aucun compte requis** et un bouton **Connexion** apparaissent sous
le logo : inscription email + mot de passe, mot de passe oublié, prénom
mémorisé, et bouton **Mes parties** qui conserve l'historique des parties
terminées par compte, consultable depuis n'importe quel appareil. Voir
[SUPABASE.md](SUPABASE.md) pour la mise en route (une requête SQL et deux
variables d'environnement) et le détail de ce qui est enregistré. Ajouter une
connexion Google plus tard est également décrit dans ce document.

Le jeu table automatiquement entre deux plis dans deux situations certaines :
une main ne contient plus que des atouts et personne d'autre n'a d'atout,
ou il n'y a plus d'atouts et toutes les cartes du joueur qui entame sont
maîtresses dans leur couleur. Les cartes restantes des quatre joueurs sont
alors révélées côte à côte auprès de leurs noms, et les plis restants sont
attribués avec le dix de der et le capot éventuel. **Voir les scores** permet
ensuite d'ouvrir le récapitulatif. Si un appareil occupe le siège plateau,
c'est sur cet appareil que les mains sont révélées.

Le dernier pli se joue automatiquement avec les quatre cartes d'un coup, sans annonce de
tablage : il faut au moins deux cartes restantes par joueur pour tabler.
Il reste visible une seconde de plus que les autres plis avant d'être ramassé.
Le récapitulatif de la dernière donne reste affiché jusqu'à validation,
avant l'annonce du vainqueur de la partie.

Les mains sont triées de la carte la plus forte à la plus faible. Une fois les
enchères terminées, les atouts passent dans l'ordre Valet, 9, As, 10, Roi,
Dame, 8, 7, avec une courte animation. Les groupes de couleurs alternent
rouge/noir autant que possible : pique, cœur, trèfle, carreau à quatre
couleurs, ou un sandwich de teintes à trois couleurs. Lorsqu'il ne reste plus
que deux couleurs, elles conservent leur ordre à l'écran.
Chaque joueur voit la table depuis sa place, avec son nom en bas et son
partenaire en face, quel que soit le siège choisi dans le salon.

Pour enchérir, choisir la couleur au-dessus du montant puis utiliser **− / +** :
80, 90… 160, 170, 180, puis **Capot**, selon les enchères encore autorisées.
Le montant reste affiché seul pour garder le panneau compact.

## Identité visuelle

Le logo de la plateforme est l'emblème monolinéaire du 10 de trèfle, rangé
dans `logo/` avec les autres variantes proposées. Il apparaît dans l'onglet du
navigateur et, sur iPhone/iPad, comme icône **« Sur l'écran d'accueil »**.

Les icônes utilisées par le navigateur sont générées à partir de l'emblème
officiel, recolorées aux couleurs du site (fond `#0a1420`, tracé `#d9a441`) :

| Fichier | Usage |
| --- | --- |
| `logo/favicon-32x32.png`, `logo/favicon-16x16.png` | Onglet du navigateur |
| `logo/apple-touch-icon.png` (180 × 180) | Écran d'accueil iOS |
| `logo/monoline-10-club.png` | Source d'origine (1254 × 1254), logo officiel |

Ces trois icônes dérivées sont dupliquées dans `frontend-github-pages/logo/`
pour la copie statique, et publiques côté Flask via la liste blanche
`ALLOWED_STATIC_FILES` dans `server.py`. Les originales ne sont pas servies.

Note : `apple-touch-icon` alimente l'icône du raccourci « Sur l'écran
d'accueil ». Un widget iOS véritablement natif demande une application, il
n'est pas accessible depuis un site web.

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

Ce qui figure autrefois dans cette section est en place : les salons
rejoignables par code ou QR code, l'interface web multi-joueurs, les bots
choisis dans le lobby et le mode plateau partagé. Voir
[DEPLOY.md](DEPLOY.md) pour le déploiement (Render + GitHub Pages).
