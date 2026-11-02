# Brooklyn contre de Belote — état actuel au 1er novembre 2026

800 parties complètes à 1000 points, sur les 50 nouvelles graines 52000–52049. Chaque version Brooklyn v1 à v4 affronte de Belote v2 et v3 sur 100 parties par confrontation, avec inversion des équipes pour chaque graine.

Le lot comprend 4 868 donnes jouées, dont 300 capots réalisés, et 216 donnes
annulées après quatre passes. Les 16 lignes de métriques (Brooklyn et de
Belote) ont été recalculées et vérifiées contre les parties brutes.

Révision des bots : `51c8d482f647d74a07d37fc8ddb91c4b0c5d8dfc`. Ce lot inclut les informations publiques de belote, le retour au partenaire ouvreur et la nouvelle protection des atouts maîtres de v4. Sur atout demandé, v4 conserve son maître et joue le plus petit atout légal ; sans maître, il prend du gagnant rapportant le plus de points, en attaque comme en défense. Les entames, coupes et versions v1/v2/v3 ne changent pas dans cette dernière correction.

Ce résultat précède la clarification suivante : en attaque, conserver le
maître lorsqu'un autre atout gagne uniquement en dernière position ; en
deuxième et troisième positions, prendre du plus gros gagnant sûr, sinon du
plus petit gagnant actuel. Les résultats
ci-dessous restent ceux de `51c8d48` et ne mesurent pas cette clarification.

Brooklyn v1 gagne 50,0 % des parties, v2 33,5 %, v3 46,5 % et v4 45,5 %.
V4 réussit 382/421 contrats à la couleur (90,7 %), 53/84 en SA (63,1 %)
et 52/72 en TA (72,2 %). Le SA demeure le mode le moins fiable.
La marge ordinaire moyenne de v4 est de +24,44 à la couleur, +4,27 en SA
et +15,12 en TA : bonne sécurité à la couleur, mais 62 % des contrats
ordinaires à la couleur finissent plus de 20 points au-dessus de l'annonce.
Cela justifie d'étudier la calibration des enchères, sans démontrer qu'une
hausse uniforme améliorerait les victoires.

V4 reste proche de v3 : écart de victoires de −1 point de pourcentage,
IC 95 % [−3 ; +1]. Face à v1, l'écart est de −4,5 points, IC [−11,5 ; +3].
Ce lot ne démontre donc ni un gain de v4 ni une supériorité certaine de v1
sur v3/v4. Les campagnes antérieures utilisent d'autres graines et révisions ;
leur variation ne mesure pas isolément la dernière correction.

## Confrontations directes

| Brooklyn | de Belote | Victoires / 100 | IC 95 % | Prise | Contrats réussis |
| --- | --- | ---: | --- | ---: | --- |
| brooklyn_v1 | spark_v2 | 53 | [46.0, 60.0] % | 55.5 % | 263/331 (79.5 %) |
| brooklyn_v1 | spark_v3 | 47 | [39.0, 55.0] % | 53.9 % | 256/326 (78.5 %) |
| brooklyn_v2 | spark_v2 | 35 | [26.0, 44.0] % | 41.5 % | 203/250 (81.2 %) |
| brooklyn_v2 | spark_v3 | 32 | [24.0, 40.0] % | 42.3 % | 202/254 (79.5 %) |
| brooklyn_v3 | spark_v2 | 48 | [39.0, 56.0] % | 47.7 % | 252/297 (84.8 %) |
| brooklyn_v3 | spark_v3 | 45 | [35.0, 55.0] % | 46.2 % | 238/282 (84.4 %) |
| brooklyn_v4 | spark_v2 | 47 | [38.0, 56.0] % | 47.3 % | 250/293 (85.3 %) |
| brooklyn_v4 | spark_v3 | 44 | [35.0, 54.0] % | 46.3 % | 237/284 (83.5 %) |

## Résultats regroupés sur les deux adversaires

| Brooklyn | Victoires / 200 | IC 95 % | Prise | Contrats réussis |
| --- | ---: | --- | ---: | --- |
| brooklyn_v1 | 100 (50.0 %) | [43.0, 57.0] % | 54.7 % | 519/657 (79.0 %) |
| brooklyn_v2 | 67 (33.5 %) | [26.0, 41.0] % | 41.9 % | 405/504 (80.4 %) |
| brooklyn_v3 | 93 (46.5 %) | [38.0, 55.0] % | 47.0 % | 490/579 (84.6 %) |
| brooklyn_v4 | 91 (45.5 %) | [37.5, 53.5] % | 46.8 % | 487/577 (84.4 %) |

## Calibration des contrats

Les capots restent inclus dans les victoires, les prises et les réussites. Seule la marge ordinaire exclut les capots réalisés. La marge est le score gagné (plis, dix de der et belote) moins le montant annoncé, avant bonus de contrat/coinche.

| Brooklyn | Mode | Réussis / pris | Réussite | Prise parmi toutes les donnes | Enchère moyenne | Marge ordinaire moyenne |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| brooklyn_v1 | SUIT | 445/541 | 82.3 % | 45.0 % | 103.44 | 18.86 |
| brooklyn_v1 | SANS_ATOUT | 37/69 | 53.6 % | 5.7 % | 102.03 | 1.87 |
| brooklyn_v1 | TOUT_ATOUT | 37/47 | 78.7 % | 3.9 % | 109.15 | 16.11 |
| brooklyn_v2 | SUIT | 268/318 | 84.3 % | 26.5 % | 99.21 | 20.42 |
| brooklyn_v2 | SANS_ATOUT | 50/78 | 64.1 % | 6.5 % | 103.46 | 3.6 |
| brooklyn_v2 | TOUT_ATOUT | 87/108 | 80.6 % | 9.0 % | 107.22 | 19.13 |
| brooklyn_v3 | SUIT | 383/420 | 91.2 % | 34.1 % | 103.95 | 24.78 |
| brooklyn_v3 | SANS_ATOUT | 54/85 | 63.5 % | 6.9 % | 100.24 | 4.27 |
| brooklyn_v3 | TOUT_ATOUT | 53/74 | 71.6 % | 6.0 % | 107.3 | 14.54 |
| brooklyn_v4 | SUIT | 382/421 | 90.7 % | 34.2 % | 103.99 | 24.44 |
| brooklyn_v4 | SANS_ATOUT | 53/84 | 63.1 % | 6.8 % | 100.12 | 4.27 |
| brooklyn_v4 | TOUT_ATOUT | 52/72 | 72.2 % | 5.8 % | 107.64 | 15.12 |

## de Belote en attaque

| de Belote | Contre Brooklyn | Prise | Contrats réussis | Enchère moyenne | Marge ordinaire moyenne |
| --- | --- | ---: | --- | ---: | ---: |
| spark_v2 | brooklyn_v1 | 44.5 % | 227/265 (85.7 %) | 102.72 | 20.56 |
| spark_v3 | brooklyn_v1 | 46.1 % | 233/279 (83.5 %) | 103.15 | 20.86 |
| spark_v2 | brooklyn_v2 | 58.5 % | 300/352 (85.2 %) | 102.3 | 21.14 |
| spark_v3 | brooklyn_v2 | 57.7 % | 298/346 (86.1 %) | 102.02 | 20.59 |
| spark_v2 | brooklyn_v3 | 52.3 % | 277/326 (85.0 %) | 102.52 | 20.3 |
| spark_v3 | brooklyn_v3 | 53.8 % | 281/328 (85.7 %) | 102.32 | 20.93 |
| spark_v2 | brooklyn_v4 | 52.7 % | 277/326 (85.0 %) | 102.58 | 20.41 |
| spark_v3 | brooklyn_v4 | 53.7 % | 283/329 (86.0 %) | 102.28 | 20.83 |

## Écarts de victoires appariés

| Comparaison | Écart en points de pourcentage | IC 95 % |
| --- | ---: | --- |
| brooklyn_v4 minus brooklyn_v1 | -4.5 | [-11.5, 3.0] |
| brooklyn_v4 minus brooklyn_v3 | -1.0 | [-3.0, 1.0] |
| brooklyn_v3 minus brooklyn_v1 | -3.5 | [-11.0, 5.0] |

## Répartition des marges ordinaires

Les tranches suivantes incluent les chutes, mais excluent les capots réalisés. Une marge positive ne garantit pas la réussite si la majorité stricte manque. La dernière colonne compte ces chutes malgré un montant numérique atteint, capots inclus.

| Brooklyn | Mode | Sous le contrat | Marge 0–9 | Marge 10–20 | Marge >20 | Chutes avec montant atteint |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| brooklyn_v1 | SUIT | 19.4 % | 13.7 % | 18.2 % | 48.7 % | 0 |
| brooklyn_v1 | SANS_ATOUT | 43.5 % | 14.5 % | 11.6 % | 30.4 % | 2 |
| brooklyn_v1 | TOUT_ATOUT | 22.2 % | 13.3 % | 20.0 % | 44.4 % | 0 |
| brooklyn_v2 | SUIT | 16.7 % | 10.2 % | 21.1 % | 52.0 % | 1 |
| brooklyn_v2 | SANS_ATOUT | 33.3 % | 17.9 % | 20.5 % | 28.2 % | 2 |
| brooklyn_v2 | TOUT_ATOUT | 21.4 % | 12.2 % | 12.2 % | 54.1 % | 0 |
| brooklyn_v3 | SUIT | 9.1 % | 13.3 % | 15.6 % | 62.0 % | 2 |
| brooklyn_v3 | SANS_ATOUT | 34.1 % | 22.4 % | 18.8 % | 24.7 % | 2 |
| brooklyn_v3 | TOUT_ATOUT | 29.6 % | 11.3 % | 14.1 % | 45.1 % | 0 |
| brooklyn_v4 | SUIT | 9.4 % | 12.5 % | 16.1 % | 62.0 % | 3 |
| brooklyn_v4 | SANS_ATOUT | 34.5 % | 21.4 % | 19.0 % | 25.0 % | 2 |
| brooklyn_v4 | TOUT_ATOUT | 29.0 % | 11.6 % | 13.0 % | 46.4 % | 0 |

## Protocole et limites

- Reproduction : `python -B benchmarks/bots.py --pairs 50 --seed 52000 --target 1000 --workers 4 --brooklyn brooklyn_v1 brooklyn_v2 brooklyn_v3 brooklyn_v4 --output results.json`.
- Moteur web, sans diffusion ni pauses visuelles ; aucun contact avec le serveur actif et aucun redémarrage. Chaque bot ne reçoit que sa main et les informations publiques habituelles. Les diagnostics consultent les mains cachées après la décision sans les transmettre aux bots.
- Réussite selon le résultat réel du moteur, y compris la majorité stricte. Prise calculée sur les donnes jouées, hors redistributions après quatre passes. Aucun échec ni capot omis. Un Capot annoncé ne fournit pas de marge numérique.
- de Belote v2/v3 enchérissent à une couleur ; ils utilisent leur politique SA/TA commune lorsqu’ils défendent ces modes. Brooklyn peut annoncer les six contrats.
- IC par bootstrap percentile de 4000 tirages, graine 20261020, en rééchantillonnant les graines entières : les deux équipes en confrontation directe, les deux adversaires et équipes dans les résultats regroupés et écarts appariés.
- Les graines sont nouvelles et aucune politique n’a été ajustée sur leurs résultats. Les anciennes campagnes utilisent d’autres graines et révisions : leurs écarts ne mesurent pas isolément la dernière correction. Même avec des graines appariées, des enchères et durées de parties différentes changent les donnes suivantes ; ceci ne remplace pas une comparaison à contrat fixé.
- Contrôle des 800 clés de partie uniques, huit confrontations de 100 parties, inversions d’équipes, totaux et réussites des tableaux contre les enregistrements bruts.
- Durée murale enregistrée : 1150.1 secondes (ce n’est pas une mesure de temps CPU).

Données : [parties brutes](results-2026-11-01-current-bots.json), [synthèse](summary-2026-11-01-current-bots.json).
