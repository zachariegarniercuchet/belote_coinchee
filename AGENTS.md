# Guide du dépôt — Belote Coinchée

## Collaboration

- Échanger en français par défaut ; conserver le vocabulaire du jeu : donne,
  pli, atout, preneur, défense, coinche, surcoinche, belote/rebelote, capot.
- Demander des précisions lorsqu'une variante de règle ou un choix de produit
  change le résultat attendu. Les règles jouées par le groupe priment sur une
  interprétation supposée des « règles officielles ».
- Réaliser les modifications demandées, les vérifier et signaler les limites
  de validation. Préserver les changements locaux et éviter les refontes sans
  rapport avec la demande.
- Maintenir ce guide lorsque l'architecture, les commandes ou les conventions
  changent. Les observations datées ci-dessous sont un état initial, à revérifier.
- Make frequent, small commits after each completed and verified logical step.
  Keep each commit focused on one change, include its relevant tests and docs,
  use a clear commit message, and never include unrelated local changes.
  Commit locally as work progresses; do not push unless the user requests it.
- Keep the test suite small and intentional. Prefer nominal, representative
  user journeys that catch several regressions over one atomic test per branch
  or implementation detail. Reuse or extend existing coverage before adding
  tests; justify additions by a meaningful behavior or regression risk.

## TODO — test-suite audit (deferred)

- Review whether each existing test protects a useful behavior and identify
  overlapping assertions, implementation-coupled tests, and maintenance cost.
- Assess coverage of nominal flows (a complete game, return to lobby and
  restart, bots, bidding, card play, scoring and claims), rather than test count.
- Propose consolidation into a few representative scenarios and retain focused
  cases only where their risk warrants it. Do this audit later; do not expand
  or reorganize the suite preemptively.

## TODO — bidding variants (deferred)

- Add Tout Atout (TA) and Sans Atout (SA): define contract modes, card strength
  and values, legal play, scoring, bot behavior and UI together.
- Générale means all eight tricks won by the bidder alone, rather than by
  their team. Keep its selector entry commented out after Capot until the
  contract rules, validation and scoring are specified and implemented.

## Architecture et points d'entrée

Application Python avec interface web en HTML/CSS/JavaScript natifs. Pas de
gestionnaire de paquets JavaScript ni d'étape de compilation du frontend.

| Emplacement | Responsabilité |
| --- | --- |
| `belote/cards.py` | Cartes, couleurs, rangs, valeurs, mélange, coupe et distribution. |
| `belote/bidding.py` | Actions et état des enchères, contrat, coinche/surcoinche. |
| `belote/trick.py` | Cartes légales, état et gagnant d'un pli, équipes. |
| `belote/claim.py` | Détection des deux cas certains de tablage et résolution légale des plis restants. |
| `belote/scoring.py` | Belote, dix de der, capot et score d'une donne. |
| `belote/game.py` | `Donne`, `DonneLog`, `Game`, cumul et fin de partie pour le moteur synchrone. |
| `belote/player.py`, `belote/human_cli.py` | Interface `Player` et joueur humain en console. |
| `belote/bots/` | Bots classiques et Spark ; catalogue/fabriques dans `registry.py`. |
| `cli.py` | Lancement d'une partie en console, humains et bots. |
| `server.py` | Application Flask, routes HTTP et événements Socket.IO. |
| `extensions.py` | Instance Socket.IO partagée, mode `threading` et configuration CORS. |
| `rooms.py` | Salons, sièges, connexions, choix des bots et verrous. |
| `game_session.py` | `NetworkGame`, `NetworkPlayer`, `GameSession` : déroulement web, attente des joueurs et diffusion des états. |
| `serialize.py` | Conversion cartes/enchères en données JSON et identifiants de cartes. |
| `index.html`, `app.js`, `style.css` | Interface principale, servie par Flask ; `index.html` utilise Jinja. |
| `frontend-github-pages/` | Copie statique de l'interface pour un backend distant. |
| `tests/test_rules.py` | Script autonome de vérification des règles et scores. |
| `tests/test_autoplay.py` | Dernière carte automatique et singletons joués manuellement sur le web. |
| `tests/test_claim.py` | Tablage, exploration des ordres légaux, équivalence des scores console/web et confidentialité des mains. |
| `tests/test_hand_order.py` | Tri par force, alternance rouge/noir et passage à l'ordre d'atout après les enchères. |
| `tests/test_lobby.py` | Un parcours Socket.IO : changement de siège, bot restauré, conflit simultané, homonymes et reconnexion. |
| `requirements.txt` | Dépendances web : Flask, Flask-SocketIO et qrcode avec Pillow. |
| `render.yaml`, `DEPLOY.md` | Configuration Render et documentation de déploiement. |
| `README.md`, `belote/bots/README.md` | Présentation, utilisation et procédure d'ajout de bots. |
| `report*.md` | Rapports existants ; les confronter au code avant de s'y fier. |

## Commandes utiles

Depuis la racine, sous PowerShell, créer un environnement local si nécessaire :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B server.py
```

Ouvrir `http://localhost:5000`. Le serveur écoute sur `0.0.0.0` ; le port est
configurable avec `PORT`. Pour la console :

```powershell
python -B cli.py
```

Vérifications disponibles sans installer les dépendances web :

```powershell
python -B tests/test_rules.py
node --check app.js
node --check frontend-github-pages/app.js
```

Avec un environnement virtuel, remplacer `python` par son exécutable. Le test
de règles est un script avec compteurs et code de sortie, pas une suite
`unittest` : vérifier son résultat et son code de sortie. Les commandes Node
vérifient seulement la syntaxe. Aucun linter ou outil de formatage n'est
configuré dans le dépôt à l'initialisation.

Tests de l'automatisme web (avec les dépendances de `requirements.txt`) :

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_autoplay.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_claim.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_hand_order.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_lobby.py
```

## Conventions et précautions d'implémentation

- Conserver le moteur `belote/` indépendant de Flask, du réseau et du DOM.
  Centraliser les règles dans ses modules existants.
- Le déroulement d'une donne est présent à la fois dans `belote/game.py` et
  `NetworkGame` dans `game_session.py`. Pour une modification de déroulement,
  vérifier les chemins console et web.
- Quatre joueurs, sièges `0` à `3` : équipe 0 = `0/2`, équipe 1 = `1/3`.
  Le siège optionnel `"board"` affiche le plateau sans main ni action de jeu.
  Chaque joueur voit son propre siège en bas et son partenaire en face ; les
  attributs `data-position` des marqueurs et emplacements de cartes assurent
  cette rotation visuelle sans modifier les identifiants de sièges du jeu.
  Le plateau partagé conserve la vue de référence du siège 0.
- Le serveur valide les choix et fournit les actions légales. Ne pas déplacer
  la validation exclusivement dans le frontend ni envoyer les mains adverses
  dans les états communs pendant le jeu. Seul un tablage certain révèle les
  quatre mains restantes via `claim.hands`. Préserver les états individualisés
  par siège hors de ce cas.
- Le fil de partie attend les choix humains via `threading.Event` ; salons et
  sessions utilisent des verrous. Vérifier la synchronisation pour les attentes,
  reconnexions, fins de donne et changements de session.
- Les événements principaux sont `create_room`, `join_lobby`, `take_seat`,
  `leave_seat`, `set_bot`, `start_game`, `bid_choice`, `play_card`,
  `request_state`, `dismiss_recap`, `new_game`. Les clients reçoivent notamment
  `lobby_update`, `state_update` et `error_message`.
- Préserver les identifiants échangés : carte sous la forme `VALET_PIQUE`,
  index d'enchère issu de la liste légale courante, clés de sièges/équipes
  converties en chaînes dans les objets JSON. Coordonner toute évolution du
  protocole entre serveur, sérialisation et interfaces.
- Pour ajouter un bot, suivre `belote/bots/README.md`, implémenter `Player` et
  passer par `belote.bots.create_bot` / `list_bots`. Conserver les imports
  paresseux des fabriques. Le bot par défaut est actuellement `spark_v3`.
- Pour une modification d'interface, examiner les deux versions du frontend
  et appliquer les changements partagés aux deux. Préserver les différences
  nécessaires entre Jinja et hébergement statique ; ne pas écraser une copie
  par l'autre sans examiner le diff.
- Préserver les textes français et leurs accents en UTF-8, ainsi que
  l'utilisation sur téléphone et le mode plateau partagé.
- Ajouter ou adapter des vérifications ciblées pour les changements de règles.
  Pour le web, vérifier selon le périmètre : création/jonction de salon,
  choix de siège, bots, enchères, carte légale, récapitulatif et reconnexion.
  Indiquer explicitement si une vérification navigateur n'a pas été faite.
- Des fichiers `__pycache__/*.pyc` sont déjà suivis par Git. Utiliser `python -B`
  lors des vérifications pour éviter de les modifier ; ne pas les inclure dans
  les changements fonctionnels. Ne pas versionner `.venv` ni les poids ML.

## Règles et configuration actuelles

Dans le salon, une connexion n'occupe qu'un siège, plateau compris. Le serveur
vérifie puis déplace sous le même verrou : si la destination est prise, garder
la place précédente et signaler le refus. Libérer aussi le prénom de l'ancienne
place ; son bot configuré reste mémorisé. Deux demandes concurrentes ne peuvent
pas prendre la même place, même avec des prénoms identiques. Chaque état de
salon est personnalisé avec `your_seat` ; le client attend cette confirmation
et ne déduit pas son siège du prénom. Pendant la partie, interdire changements
et départs, mais permettre la reconnexion à son siège réservé.

Le formulaire d'enchères web affiche les couleurs au-dessus d'un montant
unique, ajusté par −/+. Les crans viennent des actions légales du serveur :
80 à 180 par dizaines, puis Capot, en partant du minimum encore autorisé.
Le moteur acceptait déjà 170 et 180. Chaque nouveau tour d'enchère et chaque
nouvelle donne repartent du minimum légal, même si les actions sont identiques.
La sélection est conservée lors des diffusions identiques d'un même tour.
La couleur présélectionnée est celle de la dernière enchère du partenaire
(siège opposé), en ignorant ses passes/coinches et les enchères des autres.
Sans couleur annoncée par le partenaire, ou si elle n'est plus légale, garder
la première couleur autorisée (pique normalement). Le joueur reste libre de
changer ce choix ; le montant initial reste le minimum légal.
L'entrée Générale reste commentée après Capot dans
les deux interfaces ; TA/SA et Générale sont suivis dans les TODO ci-dessus.

`serialize.sorted_hand` trie les mains affichées sans modifier les mains du
moteur : force décroissante, ordre d'atout seulement après la fin des enchères,
et alternance maximale rouge/noir entre les couleurs présentes. L'ordre de
référence est pique/cœur/trèfle/carreau ; à trois couleurs, la couleur isolée
est placée entre les deux couleurs de même teinte. À deux couleurs ou moins,
conserver leur ordre précédent : la session mémorise l'ordre par siège et par
donne, y compris pour les reconnexions et le tablage. Le tri de force au sein
d'une couleur reste actif. Les mains révélées au
tablage suivent aussi l'ordre de force de l'atout.
Les deux interfaces conservent les éléments DOM des cartes par identifiant et
animent les changements d'ordre sur 420 ms. Respecter la préférence de mouvement
réduit et vérifier les actions sur l'état courant, sans accumuler de gestionnaires
de clic/glissement lors des mises à jour Socket.IO.

Les annonces (tierce, cinquante, cent, carré) et les variantes Sans Atout /
Tout Atout ne sont pas implémentées. La belote/rebelote est attribuée
automatiquement au détenteur du roi et de la dame d'atout en main initiale.
Cette détection reste privée : envoyer `belote_team` et `belote_holder_seat`
à `null` tant qu'aucune carte de la paire n'a été annoncée et que le bilan
de la donne n'est pas disponible. Masquer à la source, pas seulement en CSS,
pour ne pas révéler les cartes adverses dans les états Socket.IO.
Sur le web, le serveur ajoute une entrée à `belote_announcements` quand ce
joueur pose réellement la première puis la seconde carte de sa paire :
« Belote ! », puis « Rebelote ! », dans l'ordre roi/dame ou dame/roi. Le client
affiche une bulle de 3,2 s près de son marqueur, sans répéter l'annonce lors
des mises à jour et sans rejouer une ancienne annonce après ramassage.
La bulle est décalée en diagonale à droite du joueur (vers l'intérieur au
bord droit), indépendamment de sa carte. Conserver les bulles dans le DOM
sur les états identiques ; chaque nouvelle enchère, même « Passe » répété,
relance sa courte disparition/réapparition.
Les cartes simulées après tablage ne déclenchent pas ces bulles.
Ne pas modifier ces choix sans demande correspondante.

Les cartes posées suivent la taille réelle du plateau via `ResizeObserver`
(largeur et hauteur disponibles, de 24 à 62 px de large), avec un repli CSS
adaptatif. Leurs emplacements restent proportionnels au plateau et tournés
selon le siège ; ce dimensionnement ne touche pas les cartes en main.

Sur le web, `NetworkPlayer.choose_card` joue automatiquement la dernière carte
de la main après une pause de 0,6 seconde (`AUTO_CARD_PLAY_DELAY`), aussi à
l'entame, en coupe et en défausse. Le jeu automatique des singletons de la
couleur demandée est temporairement désactivé : son code est conservé en
commentaire à la demande de l'utilisateur. Lorsqu'il reste plusieurs cartes
en main, le joueur doit confirmer sa carte, même s'il n'existe qu'une carte
légale.

Le tablage est détecté entre deux plis, uniquement s'il reste au moins deux
cartes par joueur, dans `belote/claim.py`, utilisé par la console et le web.
Le dernier pli web est posé automatiquement en une seule diffusion des quatre
cartes, sans attente des joueurs ou bots ni annonce de tablage. Le client conserve
les mêmes éléments DOM pendant le pli, y compris sur les diffusions identiques.
Il regroupe les quatre cartes puis les ramasse vers la position réelle du tas
gagnant A/B (1 000 ms), après une pause de 350 ms, ou 1 350 ms au dernier pli.
Synchroniser cette seconde supplémentaire dans `trickCollectionDelay` avec
`LAST_TRICK_EXTRA_PAUSE` côté serveur. En mouvement réduit, conserver la pause
mais retirer le déplacement. Deux cas de tablage seulement :
une main ne contient que des atouts
et aucun autre joueur n'en a (quelle que soit l'entame), ou aucun atout ne
reste et chaque carte du joueur qui entame est supérieure à toutes les cartes
restantes de sa couleur dans les autres mains. Les plis restants sont résolus
légalement sans demander de choix, avec historique, dix de der et capot.
Le web transmet `claim` (`seat`, `reason`, `remaining_tricks`, `hands`) et
conserve le tableau révélé jusqu'au clic local « Voir les scores », avant le
récapitulatif habituel. Si un plateau partagé est présent, il affiche ce
tableau ; les téléphones restent en mode manette. Les mains révélées sont
effacées avant la première diffusion de la donne suivante.
Les donnes intermédiaires attendent la validation du récapitulatif. La dernière
donne diffuse `final_donne` et le gagnant dès le calcul des scores, puis
`game_end` sans attendre de clic. Le même récapitulatif affiche le résultat
final, l'historique et le bouton « Retour au salon », sans seconde fenêtre.
Il reste ouvert sur les clics ordinaires, y compris sur les téléphones en mode
manette ; le tablage reste consultable avant les scores sur le plateau.
Le bouton de retour est activé une fois `game_over` reçu, lorsque la session
est effectivement terminée et peut être libérée par `new_game`.

Les salons et parties sont stockés en mémoire : un redémarrage perd leur
état ; l'architecture actuelle suppose un seul processus serveur. Variables
de configuration : `PORT`, `BELOTE_SECRET`, `CORS_ALLOWED_ORIGIN`,
`PUBLIC_BASE_URL`. Le frontend peut lire `window.BELOTE_BACKEND_URL` pour
Socket.IO. Consulter `DEPLOY.md` pour les deux modes d'hébergement, et
vérifier le code pour le comportement effectif.

## État initial constaté le 17 octobre 2026

- Environnement inspecté : Python 3.12.10 et Node 24.15.0 ; `render.yaml`
  déclare Python 3.11.9. Flask, Flask-SocketIO et qrcode ne sont pas installés
  dans le Python inspecté ; le serveur web n'a pas été lancé.
- `python -B tests/test_rules.py` : **16 réussites, 2 échecs**, sur
  `coinche reussi - preneurs` et `coinche reussi - defense (rien sauf belote)`.
  Les attentes du script et la formule actuelle de coinche réussie divergent.
  Clarifier la règle attendue avant de changer calcul ou attentes ; ne pas
  supprimer ces vérifications pour masquer l'écart.
- Les deux fichiers `app.js` passent `node --check`.
- Les copies `app.js` divergent sur l'affichage et la fermeture du
  récapitulatif : la version principale tient compte de `board_present` et
  écoute le clic sur le document ; la copie statique écoute `board-panel`.
- La copie statique contient encore l'URL d'exemple
  `https://VOTRE-SERVICE.onrender.com`. Ses chemins HTTP de QR code et
  d'informations de salon restent relatifs à l'origine du frontend, même si
  Socket.IO utilise `BELOTE_BACKEND_URL` : vérifier ce point avant un usage
  avec frontend et backend sur des origines différentes.
- Certaines sections du README décrivent encore comme futures des fonctions
  web déjà présentes. Ce guide décrit le code observé, sans certifier la
  conformité à un règlement externe.
