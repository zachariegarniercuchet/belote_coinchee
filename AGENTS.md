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
  Commit locally as work progresses. Before EVERY push/publication, show the
  target commits and warn that deployment may interrupt games, then STOP and
  obtain a fresh, separate confirmation for publishing NOW. This applies at
  all times, not only during rule discussions. An earlier push request, a
  request to implement/benchmark, or approval of code is not continuing consent
  to publish later. Do not push while awaiting that final timing confirmation.
- Keep the local pre-push gate enabled (`core.hooksPath=.githooks`). Verify it
  before any publication. Never use `--no-verify`, disable/change the hook path,
  invoke a different publication route, or auto-answer the gate to evade it.
  Supply its exact commit confirmation only after the user's fresh approval
  for that push. Git hooks are local: on a fresh clone, inspect existing hooks
  before enabling this path; preserve any existing checks rather than replacing
  them silently. See README.md. Do not push merely to publish the gate itself.
- Keep the test suite small and intentional. Prefer nominal, representative
  user journeys that catch several regressions over one atomic test per branch
  or implementation detail. Reuse or extend existing coverage before adding
  tests; justify additions by a meaningful behavior or regression risk.

## TODO prioritaire — Sans Atout : jeu de carte et calibration

- Revoir en profondeur le jeu de carte SA : David signale des parties où
  Brooklyn v5 perd ses as. Reproduire ces pertes et distinguer les coups
  forcés des mauvais choix ; ne pas conclure à une régression propre à v5
  sans comparer les mêmes situations et la politique SA partagée.
- Réexaminer quand encaisser ou conserver un as, les entames, les purges,
  l'établissement des couleurs, les reprises de main et le soutien au
  partenaire. Le principal problème signalé est le jeu de carte.
- Recalibrer aussi les enchères SA : trois as sans dix constituent pour
  David un repère à 80 SA plutôt que 90. Examiner le reste de la main avant
  de définir les exceptions ; ne pas augmenter globalement l'ambition.
- Vérifier les corrections sur quelques donnes nominales représentatives,
  puis comparer avant/après à cartes et contrat identiques pour isoler le
  jeu de carte, et en parties complètes pour les enchères. Garder la suite
  de tests petite ; ne pas ajouter un test atomique pour chaque branche.
- La revue globale reste à faire. Le correctif ciblé de v5 décrit plus bas
  traite la charge en dernière position et les reprises du partenaire ; il
  ne constitue pas une refonte des entames, purges ou enchères SA. Le TA
  garde sa politique existante.

## TODO — test-suite audit (deferred)

- Review whether each existing test protects a useful behavior and identify
  overlapping assertions, implementation-coupled tests, and maintenance cost.
- Assess coverage of nominal flows (a complete game, return to lobby and
  restart, bots, bidding, card play, scoring and claims), rather than test count.
- Propose consolidation into a few representative scenarios and retain focused
  cases only where their risk warrants it. Do this audit later; do not expand
  or reorganize the suite preemptively.

## TODO — Brooklyn defensive cutting variant (deferred)

- Explore a future Brooklyn defensive cutting policy: preserve trump
  control when there is spare length, but cash vulnerable 9/ace points when
  they are likely to be lost. Implement separately, preserving v1/v2/v3/v4/v5;
  do not apply a blanket cheapest-cut rule in defence.

## TODO — bidding variants (deferred)

- Soutien Brooklyn v5 après notre annonce puis changement de couleur du
  partenaire : étudier une petite prime pour deux dix. Préciser le montant
  et la protection nécessaire (dix seconds, longueur, etc.) avant de l'activer.
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
| `game_export.py` | Format JSON d'analyse des donnes terminées, enchères complètes et plis résolus après tablage distingués. |
| `index.html`, `app.js`, `style.css` | Interface principale, servie par Flask ; `index.html` utilise Jinja. |
| `auth.js` | Comptes optionnels Supabase : connexion/inscription email, mode invité, historique. Fichier identique dans les deux frontends, chargé après `app.js`. |
| `logo/` | Emblème source du 10 de trèfle (originaux) et icônes dérivées : favicons 16/32 px et icône Apple 180 px, recolorées aux couleurs du site. |
| `frontend-github-pages/` | Copie statique de l'interface pour un backend distant. |
| `supabase/setup.sql`, `SUPABASE.md` | Table `game_history` avec RLS et guide de mise en route des comptes (Render, GitHub Pages, Google plus tard). |
| `tests/test_rules.py` | Script autonome de vérification des règles et scores. |
| `tests/test_autoplay.py` | Dernière carte automatique, singletons manuels et redistribution après quatre passes sur le web. |
| `tests/test_claim.py` | Tablage, exploration des ordres légaux, équivalence des scores console/web et confidentialité des mains. |
| `tests/test_game_export.py` | Parcours Socket.IO d'export JSON : donnes annulées, couleur/SA/TA, surcoinche, tablage, rejeu légal, scores et reconnexion. |
| `tests/test_hand_order.py` | Tri par force, alternance rouge/noir et passage à l'ordre d'atout après les enchères. |
| `tests/test_brooklyn.py` | Stratégie de David, enchères de partenariat v2 et parties légales identiques console/web. |
| `benchmarks/bots.py`, `benchmarks/README.md` | Comparaison reproductible des bots via le moteur web, calibration des contrats et diagnostic des entames à l'atout, sans toucher au serveur actif. |
| `benchmarks/cardplay.py` | Donnes en dupliqué : mêmes cartes, historique d'enchères, contrat et entame ; comparaison du jeu v1/v3/v4, contrôles de défense et SA/TA. |
| `tests/test_lobby.py` | Un parcours Socket.IO : changement de siège, bot restauré, conflit simultané, homonymes et reconnexion. |
| `tests/test_spectators.py` | Salon public : annuaire avec créateur, spectateur sans main, reprise d'un siège de bot entre deux donnes, témoin privé, fermeture automatique des salons abandonnés. |
| `tests/test_time_control.py` | Échiquier de temps du salon : réglage partagé et verrouillé au démarrage, coup forcé par le bot de secours, joueur viré quand son temps total est épuisé. |
| `tests/test_supabase_config.py` | Injection des clés Supabase dans la page, repli invité sans configuration et service de `auth.js`. |
| `tests/test_room_links.py` | QR code et lien de partage : URL publique déduite de l'hôte de la requête (Render), IP Wi-Fi en local et surcharge `PUBLIC_BASE_URL`. |
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
configurable avec `PORT`.
Le lancement direct local active `app.jinja_env.auto_reload` : les modèles
HTML sont relus à l'actualisation, sans interrompre les parties pour une
simple modification d'interface. Le code Python des bots/moteurs nécessite
toujours un redémarrage ; les imports en production gardent le cache Flask.

Pour la console :

```powershell
python -B cli.py
```

Une fois `.venv` installé, `./start-server.cmd` (ou un double-clic sous Windows)
lance le serveur depuis le dossier du dépôt, sans téléchargement ni assistant.
Conserver le terminal ouvert ; `Ctrl+C` arrête le serveur. Le lanceur conserve
les variables de configuration existantes, notamment `PORT`.

Vérifications disponibles sans installer les dépendances web :

```powershell
python -B tests/test_rules.py
node --check app.js
node --check auth.js
node --check frontend-github-pages/app.js
node --check frontend-github-pages/auth.js
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
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_game_export.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_hand_order.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_lobby.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_spectators.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_time_control.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_supabase_config.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_room_links.py
```

## Conventions et précautions d'implémentation

- Conserver le moteur `belote/` indépendant de Flask, du réseau et du DOM.
  Centraliser les règles dans ses modules existants.
- Tous les joueurs partagent `Player.contract` et les propriétés dérivées
  `is_attacking` / `is_defending` ; pas de copie de rôle dans le salon.
  Les deux moteurs appellent `notify_donne_start` avant les enchères (contrat
  remis à `None`), `notify_contract` une fois le contrat retenu, puis
  `notify_trick_result` pour chacun des huit plis, y compris tablage et dernier
  pli automatique. Une surcharge doit conserver le contrat dans `self.contract`.
  Pendant les enchères, le contrat provisoire est dans `BiddingState` fourni
  à `choose_bid`. Ces notifications ne transmettent aucune main adverse.
- `Player.notify_belote(seat, card)` est diffusé aux joueurs et bots de secours
  dès la pose réelle accompagnée de Belote/Rebelote, avant le joueur suivant.
  `public_belotes`, `belote_events` et `known_cards` mémorisent uniquement ces
  faits publics : la première annonce localise l'autre carte de la paire ;
  la seconde (ou son jeu dans un pli résolu) la retire des cartes restantes.
  Réinitialiser à chaque donne/contrat. Ne jamais fournir la détection privée
  des paires à l'acceptation du contrat, ni annoncer les cartes simulées après
  tablage. SA reste sans belote ; chaque paire TA est indépendante.
  Brooklyn utilise ces localisations pour les menaces adverses ; les mondes
  Spark v2/v3 réservent les cartes connues à leur détenteur et ne relâchent
  JAMAIS ce fait en relâchant une hypothèse d'enchère/coupe franche. Les
  simulations et ombres reçoivent les mêmes annonces publiques, pas les
  autres cartes du moteur.
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
- Les événements principaux sont `create_room` (avec `visibility`),
  `join_lobby`, `take_seat`, `leave_seat`, `set_bot`, `start_game`,
  `bid_choice`, `play_card`, `request_state`, `dismiss_recap`, `new_game`,
  `list_public_rooms` et `request_takeover`. Les clients reçoivent notamment
  `lobby_update`, `state_update`, `public_rooms` et `error_message`.
- Préserver les identifiants échangés : carte sous la forme `VALET_PIQUE`,
  index d'enchère issu de la liste légale courante, clés de sièges/équipes
  converties en chaînes dans les objets JSON, jeton d'onglet `token` joint à
  `join_lobby` et `take_seat`. Coordonner toute évolution du
  protocole entre serveur, sérialisation et interfaces.
- L'export `export_game` exige l'appartenance au salon et le `game_id` courant.
  `GameSession` publie un instantané complet après chaque donne, même annulée,
  sous son verrou ; ne jamais lire les mains de `ctx` dans le gestionnaire
  d'export. Le JSON versionné conserve les joueurs au début de chaque donne
  et distingue les plis résolus après tablage des choix effectivement joués.
  Le format est documenté dans README.md ; aucun jeton/sid ne doit y figurer.
  Le bouton « Exporter la partie (JSON) » télécharge le fichier via cet événement
  depuis les récapitulatifs des deux frontends, sans dépendre de Supabase.
- Pour ajouter un bot, suivre `belote/bots/README.md`, implémenter `Player` et
  passer par `belote.bots.create_bot` / `list_bots`. Conserver les imports
  paresseux des fabriques. Le bot par défaut est actuellement `spark_v3`.
- Pour une modification d'interface, examiner les deux versions du frontend
  et appliquer les changements partagés aux deux. Préserver les différences
  nécessaires entre Jinja et hébergement statique ; ne pas écraser une copie
  par l'autre sans examiner le diff. `auth.js` et `style.css` sont tenus
  identiques entre la racine et `frontend-github-pages/` ; `app.js` ne l'est
  pas (voir « État initial » plus bas).
- Le lien de partage et le QR code du salon viennent de `get_base_url()` dans
  `server.py` : `PUBLIC_BASE_URL` si défini, sinon l'hôte de la requête
  (schéma pris à `X-Forwarded-Proto`), et IP Wi-Fi seulement pour `localhost`,
  une IP privée ou un nom de poste. Ne pas recalculer ce lien côté frontend :
  `app.js` appelle `/room/<code>/info` et `/room/<code>/qr.png` via
  `backendUrl()` afin qu'ils visent le backend configuré, même depuis GitHub
  Pages.
- Les comptes sont **optionnels** : sans `SUPABASE_URL` ni `SUPABASE_ANON_KEY`,
  la page ne montre aucune trace de compte et `auth.js` ne charge aucune
  bibliothèque. Ne jamais rendre une connexion obligatoire pour jouer, ne
  jamais placer de clé `service_role` dans le navigateur ou dans le dépôt : la
  clé anon est publique et la protection vient des politiques RLS de
  `supabase/setup.sql`. `app.js` ne touche à l'authentification que par
  `window.BeloteAuth?.recordGameEnd(state)` en fin de partie — un no-op en
  mode invité.
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

Le catalogue des bots définit `family`, `version`, `author`, `description`,
`theme`, `avatars`, `level` (indicatif) et quatre prénoms par version dans
`belote/bots/registry.py`.
Le créateur choisit ces métadonnées. Les noms publics combinent prénom et
famille (« Charles de Belote »), sans suffixe de version pour de Belote et Brooklyn ; les
autres familles gardent leur suffixe. Ils sont identiques dans le catalogue,
le salon et la partie. Les versions restent dans les métadonnées et le
sélecteur pour distinguer les moteurs. Garder les identifiants API inchangés : l'ancien
`random` devient West v1 (cowboys), `heuristic` Bohème v1 (bobos à bonnet),
et `spark`/`spark_v1` à `spark_v3` de Belote v0 à v3 (aristos).
Les bots historiques ont Zach pour auteur ; la famille Brooklyn (`brooklyn_v1`)
est de David (Miles, Nora, Eli, Maya). Brooklyn hérite des enchères de Spark,
mais son jeu de carte est indépendant : chasse à l'atout en attaque, points
encaissés quand le pli paraît sûr, soutien au partenaire. Ne pas modifier
les versions existantes ni le bot par défaut en ajustant cette famille.
Ses portraits ne sont pas encore définis : quatre `None` dans `avatars`,
images masquées par le frontend. Les étoiles restent purement indicatives.
Le jeu de carte partagé Brooklyn v1/v2/v3/v4 charge le partenaire avec les points
susceptibles d'être perdus, pas simplement la carte de plus grande valeur.
V1/v2/v3 gardent le jeu publié : en attaque, plus petit atout légal gagnant
pour prendre, sur atout demandé comme en coupe. Ne pas les modifier pour
tester les variantes suivantes.
Brooklyn v4 (`brooklyn_v4`) hérite des enchères de v3, distingue la prise
à l'atout de la coupe et protège le dernier atout après le premier tour.
En attaque, distinguer les trois cas :
à l'entame, garder la chasse existante (J, sinon atout maître, sinon petit ;
ne pas sacrifier le 9 sous un J inconnu s'il reste un atout inférieur).
Sur atout demandé, en attaque, prendre du plus gros gagnant sûr en deuxième
ou troisième position (normalement un maître, ou aucune reprise adverse
possible selon les informations publiques). Sans gagnant sûr, prendre du
plus petit gagnant actuel. En quatrième position,
conserver un maître détenu et jouer le plus petit atout légal gagnant.
Sans gagnant disponible, préserver aussi le futur maître en sous-fourniture.
En défense, la conservation du maître s'applique à toutes les positions.
Un maître forcé reste joué. Les maîtres sont déduits des cartes publiques,
y compris celles du pli courant : le 9 devient maître après la chute du J.
En quatrième position, ou en défense, sans maître détenu, prendre du gagnant
rapportant le plus de points.
En coupe ou surcoupe d'une couleur annexe, l'attaque prend du plus petit
atout légal gagnant, même en dernier (R avant J si R suffit) ; la politique
de coupe en défense reste inchangée. Conserver
la priorité de charger un partenaire déjà maître quand cela reste légal.
Dans v4, distinguer le seul atout avant le premier tour d'atout et le dernier
atout après ce tour : avant, chasser normalement ; après, à l'entame, garder
le dernier atout si une couleur annexe est jouable, SAUF pour revenir à la
couleur annoncée en premier par le partenaire tant qu'un adversaire peut
encore avoir de l'atout. Sans atout adverse possible, ne pas chasser.
Fourniture, coupe obligatoire et surcoupe restent imposées par les
cartes légales. Le marqueur est public et réinitialisé à chaque donne.
Hors atout, pour prendre soi-même : plus gros gagnant en dernière position ; avant cela,
plus gros gagnant jugé sûr sur informations publiques, sinon plus petit gagnant
actuel (R avant 10 si l'as n'est pas sorti). Garder la protection contre une
coupe adverse connue ; cette estimation n'utilise jamais les mains cachées.
Garder les as hors atout par défaut ; exceptions : A–10 en main, ou as à
sauver dans les deux dernières cartes face à un risque de coupe adverse étayé
par les informations publiques. Préférer les dix lâches et honneurs non maîtres,
notamment singletons, sans sacrifier une carte maîtresse s'il reste un déchet.
Respecter les coups forcés et ne charger que si le partenaire paraît sûr.
Toute modification de ce jeu partagé exige de refaire le benchmark v1 aussi :
les anciens résultats restent attachés à leur révision, pas à un nom de bot.
Brooklyn v5 (`brooklyn_v5`) reprend les ouvertures et le socle de v4, avec
les priorités de partenaire suivantes (le jeu de v4 reste inchangé) :
- En défense à une couleur, en fourniture hors atout avant le dernier joueur,
  conserver un dix accompagné s'il est le seul gagnant actuel, qu'aucun
  gagnant n'est jugé sûr et qu'une carte légale perdante permet de laisser
  passer. Exemple : sur le Roi adverse, 10–V–7 fournit le 7 avec l'as encore
  possible derrière. Un dix sûr, en dernière position ou forcé reste joué.
  Cette protection ne change ni l'attaque, ni la fourniture à l'atout, ni SA/TA.
- Avant la dernière position, ne pas couper/surcouper volontairement le
  partenaire gagnant si une carte légale permet de le laisser gagner.
  Une incertitude sur sa carte ne justifie pas à elle seule de sacrifier
  un atout. Les coupes et montées forcées restent légales et obligatoires.
- Dans la couleur demandée, ne pas surprendre avant le dernier joueur avec
  un simple gagnant actuel non maître (10 sur R avec A encore inconnu).
- En quatrième position en défense, charger la carte légale de plus forte
  valeur susceptible d'être perdue, même si elle reprend le partenaire.
  Préserver les maîtres et séquences couvertes, ainsi que les as hors atout,
  sauf A-10 en main ou as publiquement menacé de coupe dans les deux dernières
  cartes. Quand toutes les cartes légales sont protégées, en jouer une reste
  obligatoire. Ce choix vaut à une couleur et en SA ; le TA reste inchangé.
Si le partenaire annonce une nouvelle couleur après la dernière annonce
du joueur, y compris si celle-ci était SA ou TA, son soutien ne compte que
le 9 (+10) et la belote (+20), sans valet ni as. Exception : un changement
exact de 80 à 90 autorise aussi +10 par as hors du nouvel atout. Lire les
montants à l'entrée de cet épisode de couleur, pas ceux d'une surenchère
ultérieure. Déduire les crédits déjà dépensés ; conserver le retrait de 10
sans atout. Une annonce SA décrit déjà notamment les as : ne pas les ajouter
de nouveau après le changement de couleur (90 SA → 120 trèfle n'autorise
pas 140 trèfle avec deux as sans 9 ni belote).
Après notre annonce à une couleur puis le passage du partenaire à Tout Atout,
ne soutenir que de +10 par valet et +20 par belote dans les AUTRES couleurs.
Aucun honneur ni belote de notre couleur déjà annoncée ne doit être recompté ;
les 9, as et séquences des autres couleurs n'ajoutent aucun crédit à ce soutien.
Déduire les hausses déjà dépensées dans l'épisode TA, même après une surenchère
adverse ou une nouvelle hausse du partenaire. Sans ce changement vers TA,
garder son soutien habituel ; le soutien SA reste celui de v4.
Sans changement de couleur par le partenaire, garder les enchères de v4.
Tous les choix utilisent seulement la main propre
et l'historique public. La variante défensive envisagée plus haut reste
différée et n'est pas la v5. Ne pas modifier v1/v2/v3/v4 ni de Belote en
ajustant v5 ; le bot par défaut reste inchangé.

Brooklyn v2 (`brooklyn_v2`) garde les cartes de v1 mais change les enchères :
chaque nouvelle couleur exige au moins trois atouts avec J ou 9, plus au
moins un as hors atout OU deux dix seconds. Base 80 avec un des J/9, 90
avec les deux ; le premier as hors atout est inclus dans la base, chaque
as supplémentaire ajoute +10 dès l'ouverture ou la surenchère d'entrée.
Le partenaire soutient de +10 par J/9 manquant détenu et par as hors atout.
Sans aucun atout dans la couleur du partenaire, retirer 10 au crédit total
de soutien, avec un plancher à zéro, avant de déduire les hausses déjà
dépensées. Cette décote commune à v2/v3/v4 est propre à la couleur soutenue ;
elle ne concerne ni une ouverture/changement de couleur, ni SA/TA. V1 exige
déjà au moins trois atouts pour soutenir et ne relance donc pas sans atout.
La belote compte aussi dès l'entrée. Distribution/dix seconds du premier
enchérisseur restent des crédits de rebid, comptés une seule fois.
L'as d'atout est inclus dans la base 80/90, jamais crédité de +10, ni en
soutien ni au rebid. La belote vaut +10 aux enchères avec trois atouts, +20
avec au moins quatre (son score réel reste +20). Une coupe franche n'ajoute
de crédit qu'avec au moins quatre atouts : +10, ou +20 au total pour deux.
Les mêmes
cartes ne financent pas plusieurs hausses ; les
crédits sont calculés depuis la dernière enchère de l'équipe, sans compter
une surenchère adverse comme une force supplémentaire. `partner_raises` et
`partner_raise_points` conservent les hausses publiques jusqu'à la donne
suivante. TODO : en tenir compte pour ouvrir une couleur au jeu, sans déduire
quelles cartes précises se cachent derrière ces montants. Paramètre initial :
+10 pour deux dix seconds (10 + une seule autre carte dans une couleur
secondaire). Changer de couleur est permis si sa valeur propre justifie une
enchère légale supérieure ; à valeur égale, préférer le soutien de la couleur
actuelle. Ne pas transférer les crédits du partenaire d'une couleur à l'autre ;
l'épisode de soutien repart à zéro. Mesurer prise, réussite et marge du contrat
avant de calibrer ces conventions ; voir `BROOKLYN.md`.
Brooklyn v3 (`brooklyn_v3`) utilise maintenant `_recoverable_value`, pas la
valorisation v1 : sacrifier les petites cartes aux honneurs absents, compter
les survivantes avec décote de contrôle/entrée. Hors atout, 10/R/D récupère
10/R après sacrifice de D ; R/D ne récupère rien. Un as immédiatement maître
n'est pas décoté d'établissement à cause d'une carte inférieure perdante.
Au moins trois atouts, avec J ou 9 si seulement trois. Seuils initiaux figés
avant benchmark : 30/40/50/60/70 points estimés donnent 80/90/100/110/120.
Ce ne sont ni des probabilités calibrées ni les anciens scores Spark.
Belote propre +20 une fois. Coupe : +3 par couleur vide, limitée aux atouts
restant après réserve de chasse, avec J ; aucun crédit à trois/quatre atouts.
V3 entame atout même avec un seul atout si personne n'a encore entamé atout,
ou si le partenaire a annoncé cette couleur en premier dans l'équipe.
Une coupe ne suffit pas à compter comme un tour d'atout. La conservation
du dernier atout exige donc une chasse déjà commencée et
l'absence de ce retour au partenaire ; aucune condition de fin de donne.
Le premier annonceur est relu dans l'historique public lors de l'acceptation
du contrat, y compris avant d'éventuels changements de couleur, et oublié
à la donne suivante. Ne pas le confondre avec le dernier enchérisseur.
V1/v2 restent inchangés. V3 garde la comptabilité publique de soutien de v2. Le partenaire
ajoute +10 par J/9 d'atout détenu, +10 par as hors atout et +20 pour la belote
même avec deux atouts. L'as d'atout ne compte pas en soutien. Les bonus propres
de l'ouvreur sont déjà inclus dans sa valorisation : ne pas les ajouter
encore à l'entrée/au rebid. Pas de nouveaux crédits distribution/dix seconds.
Les crédits de soutien ne se dépensent qu'une fois, restent attachés à leur
couleur, et les versions v1/v2 ainsi que le bot par défaut restent inchangés.
Le sélecteur natif est regroupé par famille et affiche les versions, pas
des prénoms différents par siège ; l'auteur et la méthode sont visibles sous
le sélecteur et dans la fiche ⓘ. Les descriptions suivent le code réel :
Spark/v1 à règles, v2 à simulations, v3 avec contraintes d'enchères et
résolution exacte de chaque répartition simulée en fin de donne.

Les 12 portraits originaux sont dans `frontend-github-pages/assets/bots/`,
avec leurs prompts de génération. Une famille partage ses quatre portraits
entre versions ; les identifiants de moteurs ne changent pas. Flask sert
uniquement les fichiers référencés par le catalogue via `/assets/bots/<fichier>`
(cache 24 h). La copie statique dispose des mêmes fichiers et peut charger
les portraits sur son backend configuré. `GameSession.bot_profiles` fournit
un profil par siège bot uniquement ; ne pas inférer les avatars des prénoms.
Conserver les éléments images entre mises à jour identiques comme les bulles.
Le salon utilise uniquement le sélecteur natif ; conserver les portraits des
bots dans le salon, à table et dans la fiche ⓘ, sans galerie de sélection.
Portraits au-dessus du nom : 48 px dans le salon, 22–30 px à table, 18 px en
paysage compact ; coins très légèrement arrondis (4 px), jamais en cercle.
Pas de photos de profil pour les joueurs humains à ce stade.
À table, les encadrés nom/portrait gardent la couleur de leur équipe réelle
(A verte, B bleue), indépendamment de la rotation. Les mêmes variables CSS
colorent les compteurs de plis, le bandeau et le statut du mode manette.
Le tour actif et le joueur qui table ont un liseré doré supplémentaire,
sans remplacer leur bordure d'équipe.

Dans le salon, une connexion n'occupe qu'un siège, plateau compris. Le serveur
vérifie puis déplace sous le même verrou : si la destination est prise, garder
la place précédente et signaler le refus. Libérer aussi le prénom de l'ancienne
place ; son bot configuré reste mémorisé. Deux demandes concurrentes ne peuvent
pas prendre la même place, même avec des prénoms identiques. Chaque état de
salon est personnalisé avec `your_seat` ; le client attend cette confirmation
et ne déduit pas son siège du prénom. Pendant la partie, interdire changements
et départs, mais permettre la reconnexion à son siège réservé.

La reconnexion ne repose ni sur le prénom ni sur le sid seuls : iOS met Safari
en veille sans fermer la WebSocket, donc le serveur détecte la déconnexion avec
retard et le joueur revient avec un **nouveau** sid alors que le siège porte
encore l'ancien. Chaque onglet génère un jeton (`sessionStorage`
`belote_token`) envoyé dans `join_lobby` et `take_seat` ; `Seat.token` le
conserve et `Room.reclaim_seat` reprend le siège **même si l'ancien sid est
encore attaché**, en expulsant la connexion périmée. Sans jeton, la reprise par
prénom n'a lieu que si le siège est libre : un homonyme ne doit jamais voler la
place. Effacer le jeton dès qu'un siège est libéré (`leave_seat`,
`release_seat_to_bot`), sinon il permettrait de reprendre une place abandonnée.
Le client mémorise aussi code + prénom (`sessionStorage` `belote_room`) et
rejoint automatiquement au rechargement ; « Quitter le salon » efface cette
entrée avant de recharger, et un salon disparu retombe sur l'accueil. Les deux
fichiers `app.js` portent cette logique à l'identique.

Un salon se crée en public ou en privé (public par défaut). Un salon privé
garde son comportement d'origine : accès par code, aucun spectateur. Un salon
public figure dans l'annuaire de l'accueil (`list_public_rooms` →
`public_rooms`) et accepte des visiteurs : une connexion sans siège y est
spectatrice, reçoit l'état public du plateau sans main ni action de jeu, et
porte `your_seat: "spectator"`. Le compteur `spectator_count` et la ligne
« N visiteurs regardent le salon » sont publics. Entre deux donnes
uniquement (`phase: "donne_end"`), un spectateur peut réserver un siège de
bot via `request_takeover` : le nom part dans `pending_takeovers`, visible de
tous, et `GameSession.apply_pending_takeovers()` permute le bot en
`NetworkPlayer` au début de la donne suivante, avant la distribution, donc le
nouveau joueur reçoit sa main. Aucune donne en cours n'est interrompue ; le
bouton n'apparaît que sur les sièges de bot occupés. Un spectateur ne redevient
jamais spectateur volontairement : il reste joueur jusqu'à la fin de la partie.

L'annuaire vit dans un rectangle séparé `#public-card` sous le panneau
principal de l'accueil (l'onglet « Salons publics » a été supprimé). Il est
toujours visible, affiche « Aucun salon » quand la liste est vide, propose un
bouton **Actualiser** et un champ prénom, et montre le créateur de chaque
salon (`created_by`, transmis par `Room` → `public_rooms`).

Les salons abandonnés sont fermés automatiquement, sans jamais interrompre une
partie ni déconnecter un joueur : `purge_expired_rooms()` dans `server.py`
ne supprime que les salons **sans partie en cours** et **sans aucune
connection humaine attachée** (détecté via `sid_info`, qui compte aussi les
joueurs de lobby d'un salon privé, non suivis sur le `Room`). Deux seuils,
mesurés depuis `Room.last_activity` (rajeuni à chaque action humaine,
création/jonction/siège/coup/déconnexion) : `EMPTY_ROOM_IDLE` (30 min) pour un
salon nu, `NO_HUMAN_IDLE` (2 h) pour un salon qui a accueilli des joueurs ou
une partie. Le balayage tourne à chaque demande d'annuaire et dans une tâche
de fond démarrée uniquement sous `__main__` (`_purge_loop`), jamais à
l'import. Ne jamais purger un salon joué : `GameSession.stop()` n'est jamais
appelé et `_wait_for_choice` attend sans timeout, un arrêt laisserait un
thread orphelin.

L'échiquier de temps se règle dans le salon, à côté du score cible, et vaut
pour toute la partie : deux sélecteurs (`#move-time`, `#total-time`) envoient
`set_time_control`, et les options sont construites depuis les presets du
serveur (`MOVE_TIME_PRESETS`, `TOTAL_TIME_PRESETS`, en secondes, 0 = illimité)
pour que la liste blanche et l'interface ne puissent pas diverger. Les valeurs
sont lues dans la salle au démarrage (`GameSession`) et verrouillées ensuite :
un refus (hors preset, partie lancée) rediffuse l'état du salon pour que le
sélecteur revienne au choix réel. Seuls les sièges humains sont chronométrés,
et le décompte ne court que pendant leur propre réflexion (enchères et cartes),
jamais pendant les pauses, le jeu des bots ni le ramassage des plis. Les
échéances sont des instants serveur (`turn_deadline` avec `server_time`) :
le client en dérive le décompte sans dépendre de l'horloge de l'appareil, et
les budgets restants partent dans `clocks` (sièges humains seulement).
Un temps par coup dépassé fait jouer le coup par un bot de secours par siège,
armé en tête de donne et nourri des mêmes notifications que les joueurs en
place (`notify_players`) : le joueur garde sa place et son budget. Un temps
total épuisé le dépossède de son siège — `release_seat_to_bot`, le bot promu
conserve la mémoire de la donne — et son client reçoit `seat_lost` pour
rester dans le salon plutôt que sur un écran de jeu sans mise à jour.

Le formulaire d'enchères web affiche les couleurs au-dessus d'un montant
unique, ajusté par −/+. Les crans viennent des actions légales du serveur :
80 à 180 par dizaines, puis Capot, en partant du minimum encore autorisé.
Le moteur acceptait déjà 170 et 180. Chaque nouveau tour d'enchère et chaque
nouvelle donne repartent du minimum légal, même si les actions sont identiques.
La sélection est conservée lors des diffusions identiques d'un même tour.
La couleur présélectionnée est celle de la dernière enchère de l'équipe
(le joueur lui-même ou son partenaire), en ignorant les passes/coinches et
les enchères adverses. Sans couleur annoncée par l'équipe, ou si elle n'est plus légale, garder
la première couleur autorisée (pique normalement). Le joueur reste libre de
changer ce choix ; le montant initial reste le minimum légal.
L'entrée Générale reste commentée après Capot dans
les deux interfaces ; la Générale reste suivie dans les TODO ci-dessus.
Le panneau d'enchères utilise trois lignes compactes : six choix de contrat,
montant −/+ sur toute la largeur, puis Coincher/Passer/Confirmer sur la même
ligne. Les deux lignes partagent trois colonnes : Coincher sous −, Passer
sous le montant, Confirmer sous +. Les trois boutons restent présents,
grisés quand l'action est illégale ;
le dernier devient Surcoincher lorsque cette action est légale. Le titre reste
accessible aux lecteurs d'écran. Taille et position sont choisies UNE FOIS
au chargement à partir de la taille de l'écran, puis verrouillées en pixels
pour toute la page, même quand annonces, actions ou tours changent. Ne pas
replacer/redimensionner le panneau à chaque état ni selon les bulles.
La fenêtre est attachée directement à `screen-game`, en position fixe
(hors du conteneur de taille du tapis). Sous 640 px de hauteur initiale,
les trois lignes sont plus compactes ; si nécessaire, leur contenu défile
dans le cadre fixe. Le mode manette garde ce même cadre dans le flux.

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

Les annonces (tierce, cinquante, cent, carré) ne sont pas implémentées.
Sans Atout et Tout Atout suivent le §11 du PDF du dépôt : `ContractMode`
est distinct de `Suit` (le paquet garde 32 cartes). `Contract.suit`,
`BidAction.suit` et `TrickState.atout` acceptent une couleur ou un mode ;
les identifiants réseau sont `SANS_ATOUT` / `TOUT_ATOUT`, symboles SA / TA.
Les deux modes interdisent les coupes ; TA impose de monter dans la couleur
demandée, même sur le partenaire. SA utilise l'ordre hors atout, avec l'as
à 19 ; TA l'ordre atout, valeurs V=13, 9=9, A=6, 10=5, R=3, D=2.
`Card.strength_index` centralise le tri par mode. Le tablage sans coupe
compare aussi cette force. Les plafonds numériques sont 160 SA, 180 couleur,
240 TA, puis Capot ; les boutons −/+ suivent les actions de la couleur/mode.
SA n'a pas de belote ; TA admet les quatre paires, y compris dans les deux
équipes. `find_belotes` renvoie couleur→siège ; `DonneResult.belote_points`
et les états web portent les montants par équipe. Les anciens champs
`belote_team` / `belote_holder_seat` restent compatibles quand uniques.
Ne révéler que chaque paire déjà annoncée (ou toutes au bilan), jamais
les autres paires parce que l'une vient de l'être. Les bulles TA précisent
la couleur et leur compteur Belote/Rebelote est propre à chaque paire.
Les bots utilisent un jeu SA/TA commun dans `belote/bots/contract_modes.py`
sans passer dans leur ancienne chasse ni dans les simulations Spark prévues
pour une couleur d'atout unique. Les règles des contrats à une couleur
restent inchangées. `tests/test_contract_modes.py` couvre deux parcours :
règles/enchères et donnes complètes console/web avec tous les bots,
confidentialité des belotes et historique consultable.
Brooklyn v1/v2/v3/v4 peuvent aussi ouvrir et soutenir SA/TA via
`brooklyn_modes.py`. Ce module ne remplace pas leurs évaluations à une
couleur. Il exige deux cartes immédiatement maîtresses (séquences depuis
l'as en SA, depuis le valet en TA) ; SA accepte aussi trois couleurs arrêtées
par un as, un dix au moins second ou un roi au moins troisième. Il estime les
survivantes après sacrifice aux honneurs absents : 85 % immédiates, 55 % à
établir, ou 65 % pour les dix protégés / rois au moins troisièmes en SA.
SA retire 10 par couleur vide, 4 par singleton sans as, 2 par autre couleur
sans arrêt. Cinq cartes immédiatement maîtresses divisent ces pénalités par
deux ; une séquence maîtresse d'au moins sept cartes les annule si le joueur
est lui-même à l'entame initiale (information publique issue du donneur).
Une coupe franche n'est donc pas une interdiction absolue. TA garde son
évaluation et ses belotes, sans crédit de coupe. 30 points estimés donnent
80, puis +10 d'enchère par tranche de 10 estimés ; ce sont des paramètres
de développement, pas des probabilités calibrées.
Soutien : +10 par carte d'une séquence immédiatement maîtresse, +20 par
belote TA. SA ajoute +10 par dix exactement second sans as et +10 par paire
de rois au moins troisièmes hors séquence déjà comptée ; ne jamais compter
deux fois un honneur de la même main. Ces crédits sont dépensés une seule fois depuis la dernière enchère
de l'équipe, remis à zéro sur changement de mode/couleur. L'ouvreur ne
recompte pas sa propre belote au rebid. À montant égal garder son choix
historique ; une coinche évaluée pour une couleur n'est pas utilisée pour
SA/TA. Un capot SA/TA n'est annoncé que si les huit cartes sont maîtresses.
Les historiques de benchmark antérieurs à SA/TA ne mesurent pas ce choix
de six contrats ; conserver leur révision et ne pas les présenter comme
les performances actuelles. Au jeu SA/TA, Brooklyn conserve les maîtresses
courtes à l'entame. Il lance une purge avec trois cartes et les deux plus
fortes restantes, ou quatre cartes et la plus forte (A/10 en SA, J/9 en TA
au départ). Il mémorise la couleur à travers les pertes et reprises de main :
rejouer sa plus forte si elle est maîtresse, sinon une petite pour faire
tomber les honneurs absents et établir le reste. Continuer aussi une couleur
où les DEUX adversaires sont publiquement sans carte et le partenaire peut
encore fournir ; une seule coupe franche adverse ne suffit pas. La mémoire
`mode_purge_suits` est réinitialisée à chaque donne/contrat. Sinon, entamer
un déchet pour établir une couleur, sans encaisser systématiquement un
as SA/valet TA court. Le jeu en fourniture et les obligations TA restent
inchangés. Les autres familles gardent leur jeu SA/TA initial.
La belote/rebelote est attribuée
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
À la fin des enchères, diffuser la dernière annonce puis rester en phase
`bidding` pendant `FINAL_BID_READ_PAUSE` (1,5 s), sans joueur en attente, avant
le premier pli ou le ramassage d'une donne passée. Les bulles sont ensuite
retirées à la sortie des enchères, pas avant ce temps de lecture. Réarmer
leur nettoyage à l'entrée des enchères, même après la phase `dealing`.
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

Le bouton « Voir les mains et les plis » du récapitulatif ouvre une vue de
consultation : quatre mains initiales autour d'un carré, regroupées par
couleur et triées selon l'atout du contrat, avec le joueur courant en bas.
Un sélecteur permet de revoir les donnes terminées de la partie en cours ;
les donnes passées sans contrat sont exclues. `completed_deals` ne contient
que des logs avec résultat et contrat, et n'est envoyé qu'en `donne_end` ou
`game_end` (liste vide pendant le jeu). Ne jamais y inclure la donne courante
inachevée. Fermer la consultation ne valide pas le récapitulatif ; conserver
les contrôles clavier, les couleurs d'équipe et les deux frontends.
Le récapitulatif capture ses interactions et son défilement vertical
(souris/tactile), même entre deux donnes. Un clic dans son contenu ou sa
barre de défilement ne valide jamais la donne ; utiliser « Donne suivante »
ou le fond extérieur. La fin de partie garde uniquement le retour au salon.
Le bilan explique une chute (montant insuffisant, majorité non atteinte,
capot non réalisé) sans annoncer un zéro fictif quand la belote est conservée.
La consultation parcourt directement les plis : deux flèches ← / → de 0 à 8,
sans case à cocher ni curseur. Un clic affiche les quatre cartes, numérotées
dans l'ordre réel de jeu, avec une aura dorée autour de la gagnante.
Les mains restantes conservent leur tri initial. Changer de donne revient
aux mains initiales. Les compteurs A/B entourent la main du partenaire ;
ils indiquent les points de la donne après le pli affiché, belotes et dix
de der compris (100 en cas de capot), sans les primes de contrat.
`completed_deals.tricks` contient cartes, gagnant, points des cartes et
`team_points` cumulés côté serveur ; ne pas dupliquer les règles de score
dans le frontend. Ces données ne sont envoyées qu'au récapitulatif.
Le champ `claimed` signale les fins tablées dont les derniers plis ont été
résolus automatiquement, afin de distinguer cette résolution du jeu effectif.

Les salons et parties sont stockés en mémoire : un redémarrage perd leur
état ; l'architecture actuelle suppose un seul processus serveur. Variables
de configuration : `PORT`, `BELOTE_SECRET`, `CORS_ALLOWED_ORIGIN`,
`PUBLIC_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`. Le frontend peut lire
`window.BELOTE_BACKEND_URL` pour Socket.IO et `window.BELOTE_SUPABASE` pour
les comptes. Consulter `DEPLOY.md` pour les deux modes d'hébergement et
`SUPABASE.md` pour les comptes, et vérifier le code pour le comportement
effectif.

Les comptes sont facultatifs. Sans les deux variables Supabase, `auth.js`
retire le bandeau de compte dès le chargement et ne charge aucune
bibliothèque : l'écran d'accueil est strictement celui d'avant. Avec la
configuration, l'accueil affiche « Invité · aucun compte requis » et un bouton
**Connexion** qui ouvre une modale à deux onglets (Connexion / Créer un
compte, avec prénom facultatif), plus **Mot de passe oublié** (lien email,
puis écran « Nouveau mot de passe »). Une session reste ouverte d'une visite à
l'autre, le prénom du compte pré-remplit les champs de jeu, et le compte
connecté propose **Mes parties** et **Déconnexion**. Chaque partie terminée
insère une ligne dans `game_history` (clé anti-doublon `game_id` diffusée par
`GameSession`) : aucune écriture n'a lieu en mode invité. L'inscription est
ouverte ; la connexion Google n'est pas encore câblée, la procédure est dans
`SUPABASE.md`.

Après quatre passes, `donne_annulee` dure 1,4 s pour ramasser les cartes au
centre ; la donne suivante commence en phase `dealing` pendant 1,4 s avant
`bidding`. Synchroniser `REDEAL_STAGE_PAUSE` avec l'animation cliente (1,2 s).
Pas de fenêtre modale pour une donne annulée. Le client anime uniquement des
dos de cartes (32 au plateau, 8 pour sa main en mode manette), masque sa main
pendant la transition et ne révèle aucune main adverse. Dédupliquer par numéro
de donne/phase et nettoyer à la navigation ; en mouvement réduit, afficher
seulement le message sans déplacement de cartes. Un parcours représentatif
vérifie deux donnes passées, le donneur suivant, les phases, scores et états publics.

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

## Mise à jour du 19 octobre 2026 — comptes optionnels

- Environnement : Python 3.12.10 du `.venv` (Flask 3.1.3, Flask-SocketIO
  5.6.1, qrcode, Playwright 1.64 avec Chromium) et Node 24.15.0.
- `python -B tests/test_rules.py` : **16 réussites, 2 échecs** — les mêmes
  deux échecs connus que le 17 octobre, inchangés par cette livraison.
- Tous les `unittest` passent, `test_supabase_config.py` en tête (3 tests) ;
  `node --check` passe sur les quatre fichiers JS (`app.js`, `auth.js`, et
  leurs copies statiques).
- Vérification navigateur **faite** avec Playwright/Chromium sur
  `http://localhost:5000` (clés Supabase factices) et sur la copie statique
  servie sans configuration : bandeau invité, ouverture de la modale, onglet
  inscription, message d'erreur propre sur un appel réseau échoué, fermeture,
  création de salon invité inchangée, aucune exception JS, et aucune trace de
  compte visible sans configuration (18 vérifications, 0 échec).
- Vérification navigateur **faite** avec les vraies clés du projet
  (`https://rluiqgmrchewlyipioze.supabase.co`) : bandeau invité, échec de
  connexion réel traduit (« Email ou mot de passe incorrect. »), inscription
  traitée (le SMTP intégré a répondu « email rate limit exceeded », message
  traduit), demande de mot de passe oublié, création de salon invité, aucune
  exception JS (10 vérifications, 0 échec).
- Vérification navigateur **faite en bout à bout** le 19 octobre, après
  exécution de `supabase/setup.sql` et désactivation temporaire de
  « Confirm email » : inscription → session connectée (bandeau
  « Zozo / Mes parties / Déconnexion »), prénom du compte pré-rempli dans les
  champs de jeu, historique vide, `recordGameEnd` qui insère une ligne
  réellement lue ensuite (1 victoire sur 1, 1000 – 745, salon E2E0), puis
  déconnexion, reconnexion avec retrouvaille de l'historique, création de
  salon, aucune exception JS (**16 vérifications, 0 échec**). « Confirm email »
  est resté désactivé par choix produit (voir `SUPABASE.md`, étape 1).
- Vérification navigateur **faite sur la production** après push et
  redéploiement Render : `auth.js` servi, `window.BELOTE_SUPABASE` renseigné
  depuis les variables du service, bandeau invité, modale et onglets, échec de
  connexion réel traduit depuis l'origine de production (CORS OK), création de
  salon, aucune exception JS (**9 vérifications, 0 échec**).
- Reste à vérifier : un lien de confirmation réel si « Confirm email » est
  rallumé, le déploiement de la copie GitHub Pages (ses clés sont renseignées
  mais son hébergement n'a pas été testé ici), et un SMTP externe avant
  d'ouvrir les inscriptions à plusieurs (limite horaire du SMTP intégré).
  Un compte de test `e2e.1792447462@gmail.com` existe et peut être supprimé
  dans Authentication → Users ; les inscriptions précédentes avaient été
  bloquées (adresse invalide puis limite d'emails) et n'avaient rien créé.

## Mise à jour du 31 octobre 2026 — annuaire sous le panneau et fermeture des salons

- Annuaire déplacé : l'onglet « Salons publics » a disparu, la liste vit
  dans `#public-card` sous `.home-card`, toujours visible, avec « Aucun
  salon », **Actualiser**, champ prénom et créateur (`created_by`).
  `style.css` resynchronisé entre les deux frontends.
- Fermeture automatique des salons abandonnés : `purge_expired_rooms()` et
  `_purge_loop()` dans `server.py`, seuils `EMPTY_ROOM_IDLE` (30 min) /
  `NO_HUMAN_IDLE` (2 h) dans `rooms.py`, jamais pendant une partie ni avec
  un humain connecté.
- Tests : `test_spectators.py` (2), `test_lobby.py`, `test_time_control.py`,
  `test_autoplay.py`, `test_claim.py`, `test_hand_order.py`,
  `test_supabase_config.py` — tous OK.
- **Échec préexistant** : `tests/test_contract_modes.py` échoue (10
  échecs, RNG/moteur) **avec et sans** les changements de cette livraison
  (vérifié via `git stash`). Distinct des 2 échecs connus de `test_rules.py`.
  Ne pas le faire passer en touchant au moteur sans demande explicite.
- Vérification navigateur **faite** : accueil (12/12) — onglet absent,
  carte sous le panneau, message vide, création de salon Zoé présente avec
  « par Zoé », aucune erreur JS ; purge (3/3) — serveur démarrant avec la
  purge câblée, annuaire et salon créé fonctionnels. Les seuils 30 min / 2 h
  sont couverts par l'unitaire (horloge manipulée), pas par le navigateur.

## Mise à jour du 31 octobre 2026 — QR code et lien de partage

- Bug constaté : le QR code du salon encodait une URL locale.
  `get_base_url()` retombait sur `LAN_IP`, c'est-à-dire l'adresse interne du
  conteneur Render, `PUBLIC_BASE_URL` étant vide dans `render.yaml` : le scan
  ouvrait un serveur injoignable au lieu de
  `https://belote-coinchee-g77g.onrender.com`.
- Correctif serveur : `get_base_url()` déduit l'URL de l'hôte de la requête.
  Un hôte public est repris tel quel avec le schéma de `X-Forwarded-Proto`
  (Render) ; `LAN_IP` reste réservée à `localhost`, à une IP privée, à un nom
  de poste et à un nom `.local`, comme avant. `PUBLIC_BASE_URL` garde son rôle
  de surcharge (laisser vide sur Render, renseigner seulement pour viser une
  autre adresse, par exemple GitHub Pages).
- `app.js` (racine et `frontend-github-pages/`) : nouvelle fonction
  `backendUrl()` qui préfixe `/room/<code>/info` et `/room/<code>/qr.png`
  (comme elle le faisait déjà pour les portraits de bots). Sans elle, la copie
  statique demandait ces URLs à GitHub Pages, qui renvoie 404.
- `frontend-github-pages/index.html` : `window.BELOTE_BACKEND_URL` passe de
  l'exemple `https://VOTRE-SERVICE.onrender.com` à
  `https://belote-coinchee-g77g.onrender.com`.
- Tests : nouveau `tests/test_room_links.py` (2 tests : lien public derrière
  le proxy Render et PNG du QR comparé octet à octet, puis IP Wi-Fi en local
  et surcharge `PUBLIC_BASE_URL`). Suites relues : `test_autoplay.py`,
  `test_claim.py`, `test_hand_order.py`, `test_lobby.py`,
  `test_spectators.py`, `test_time_control.py`, `test_supabase_config.py`,
  `test_room_links.py` — tous OK ; `test_card_play_rules.py` 17/0 ;
  `test_rules.py` toujours 16 réussites / 2 échecs connus ;
  `test_contract_modes.py` toujours ses 10 échecs préexistants ;
  `node --check` OK sur les quatre fichiers JS.
- Vérification navigateur **non faite** pour ce changement : le QR n'a pas été
  scanné depuis un téléphone. L'URL encodée est couverte par
  `test_room_links.py` (PNG comparé) et par l'inspection de la page servie
  par Render ; un redéploiement est nécessaire pour confirmer en conditions
  réelles.

## Mise à jour du 1er novembre 2026 — reprise du siège après suspension

- Bug constaté sur iPhone : parti de la partie dans WhatsApp puis revenu dans
  Safari, le joueur était repassé spectateur (« choisis un siège ») et la
  table restait bloquée sur son siège.
- Cause : iOS met Safari en veille sans fermer la WebSocket. Le serveur
  détecte la déconnexion avec retard, donc `join_lobby` retrouvait le siège
  encore tenu par l'ancien sid, ne reprenait rien (`seat.sid is None`
  requis) et le joueur devenait spectateur ; `take_seat` refusait aussi, et
  rien ne réessayait ensuite. `Room.rebind_sid` existait déjà mais n'était
  jamais appelée.
- Correctif : jeton d'onglet en `sessionStorage`, joint à `join_lobby` et
  `take_seat`, conservé dans `Seat.token` ; `Room.reclaim_seat` reprend le
  siège même avec un ancien sid vivant. Effacé quand le siège est libéré.
  Code + prénom mémorisés pour reprendre après un rechargement ; « Quitter
  le salon » les efface.
- Le bot de secours ne joue toujours qu'à l'expiration du temps réglé :
  aucun délai de grâce n'a été ajouté, `_wait_for_choice` et
  `_wait_for_recap` restent sans timeout et une partie sans échiquier de
  temps attend toujours indéfiniment un joueur parti. Choix explicite de
  l'utilisateur ; à revoir s'il faut un relais.
- Tests : `test_lobby.py` (2, dont le nouveau
  `test_stale_seat_is_reclaimed_by_session_token`), `test_spectators.py`,
  `test_time_control.py`, `test_autoplay.py`, `test_claim.py`,
  `test_hand_order.py`, `test_supabase_config.py`, `test_room_links.py` —
  tous OK ; `node --check` OK sur les deux `app.js`, qui ne divergent que
  sur les trois écarts documentés du récapitulatif.
- Vérification navigateur **faite** (10/10, Chromium, port 5075) : siège
  pris, jeton et salon mémorisés, rechargement qui revient au même siège,
  second onglet portant le même jeton qui reprend le siège alors que la
  première connexion est encore vivante, « Quitter le salon » qui retourne
  à l'accueil en effaçant le salon mais pas le jeton, aucune erreur JS.
