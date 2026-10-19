"""
Tests dédiés au JEU DE LA CARTE (section 5 des règles officielles), et en
particulier aux 4 règles de fourniture / coupe / montée à l'atout.

Rappel des règles testées ici :

  1.  On doit toujours fournir la couleur demandée à l'entame si l'on en possède.

  2.1 Si l'on ne possède pas la couleur demandée ET que notre partenaire est
      maître du pli, on joue n'importe quelle carte (défausse libre, atout
      autorisé).

  2.2 Si l'on ne possède pas la couleur demandée ET que le partenaire n'est
      pas maître (ou n'a pas encore joué), on est tenu de couper (jouer atout)
      si l'on en possède ; sinon on défausse.
      Précision : si un adversaire a déjà coupé et qu'on n'a que des atouts
      inférieurs au sien, on n'est pas obligé d'en jouer (« on ne pisse pas »).

  3.  Quand on est conduit à jouer atout (couleur demandée = atout, OU obligation
      de couper), on doit monter au-dessus de l'atout maître déjà sur le tapis
      si c'est possible ; sinon on peut jouer un atout plus faible.

  4.  EXCEPTION : quand notre partenaire, maître, a coupé une carte adverse et
      qu'il ne nous reste QUE de l'atout, on n'est PAS obligé de fournir un atout
      supérieur : on peut jouer un atout inférieur. C'est le SEUL cas de figure
      où jouer un atout plus faible (alors qu'on possède un atout plus fort) est
      autorisé.

Conventions de table utilisées dans les tests :
  - équipes : {0, 2} et {1, 3}  -> team_of(p) = p % 2 ; partenaire de p = (p+2)%4
  - l'ordre de jeu suit le leader puis leader+1, leader+2, leader+3 (mod 4)
  - l'atout est PIQUE sauf mention contraire

Lancer avec : python tests/test_card_play_rules.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belote.cards import Card, Rank, Suit
from belote.trick import legal_cards, trick_winner

C = Card
PIQUE, COEUR, CARREAU, TREFLE = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE
V, N9, AS, D10, R, D, H8, S7 = (Rank.VALET, Rank.NEUF, Rank.AS, Rank.DIX,
                                 Rank.ROI, Rank.DAME, Rank.HUIT, Rank.SEPT)

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"ECHEC: {label}")


def same(legal, expected):
    """Compare deux listes de cartes sans tenir compte de l'ordre."""
    return set(legal) == set(expected)


# ===========================================================================
# RÈGLE 1 — fournir la couleur demandée si on la possède
# ===========================================================================

# 1a. On a la couleur demandée -> on la fournit, rien d'autre.
legal = legal_cards(
    hand=[C(AS, COEUR), C(V, PIQUE)],
    plays_so_far=[(0, C(D10, COEUR))],
    atout=PIQUE,
    current_player=1,
)
check("R1 - fournir la couleur demandee (une seule carte en main)",
      same(legal, [C(AS, COEUR)]))

# 1b. Plusieurs cartes de la couleur demandée -> toutes légales (on n'est pas
#     contraint de choisir une hauteur particulière quand on fournit).
legal = legal_cards(
    hand=[C(AS, COEUR), C(S7, COEUR), C(V, PIQUE)],
    plays_so_far=[(0, C(D10, COEUR))],
    atout=PIQUE,
    current_player=1,
)
check("R1 - fournir la couleur demandee (toutes les cartes de la couleur)",
      same(legal, [C(AS, COEUR), C(S7, COEUR)]))


# ===========================================================================
# RÈGLE 2.1 — pas la couleur demandée + partenaire maître -> défausse libre
# ===========================================================================

# Le leader (3) joue As de Coeur ; le joueur 0 (partenaire du joueur 2) fournit
# un Coeur. Le 3 est maître (As), mais le 3 n'est PAS le partenaire du 2.
# On se place au tour du joueur 1 : son partenaire est le 3, qui est maître.
# -> le joueur 1 a le droit de jouer n'importe quoi (y compris atout).
legal = legal_cards(
    hand=[C(AS, TREFLE), C(N9, PIQUE)],
    plays_so_far=[(3, C(AS, COEUR)), (0, C(D10, COEUR))],
    atout=PIQUE,
    current_player=1,
)
check("R2.1 - partenaire maitre (couleur normale) -> main entiere",
      same(legal, [C(AS, TREFLE), C(N9, PIQUE)]))


# ===========================================================================
# RÈGLE 2.2 — pas la couleur demandée + partenaire pas maître -> couper
# ===========================================================================

# 2a. Partenaire pas maître, aucun atout sur le tapis -> on doit couper avec
#     n'importe quel atout (aucune obligation de monter, il n'y a rien à battre).
legal = legal_cards(
    hand=[C(AS, TREFLE), C(N9, PIQUE), C(H8, PIQUE)],
    plays_so_far=[(3, C(AS, COEUR))],   # le 3 (adversaire du 0) est maître
    atout=PIQUE,
    current_player=0,
)
check("R2.2 - adversaire maitre, rien a battre -> jouer atout (tous les atouts)",
      same(legal, [C(N9, PIQUE), C(H8, PIQUE)]))

# 2b. Partenaire pas maître, PAS d'atout en main -> défausse libre.
legal = legal_cards(
    hand=[C(AS, TREFLE), C(H8, CARREAU)],
    plays_so_far=[(3, C(AS, COEUR))],
    atout=PIQUE,
    current_player=0,
)
check("R2.2 - adversaire maitre, pas d'atout -> defausse libre",
      same(legal, [C(AS, TREFLE), C(H8, CARREAU)]))

# 2c. Précision « ne pas pisser » : un adversaire a déjà coupé avec l'atout le
#     plus fort (Valet). On n'a que des atouts plus faibles -> défausse libre
#     (on n'est pas obligé de jouer un atout inférieur).
legal = legal_cards(
    hand=[C(H8, PIQUE), C(AS, TREFLE)],
    plays_so_far=[
        (3, C(AS, COEUR)),    # entame Coeur
        (0, C(D10, COEUR)),   # le partenaire du 2 fournit
        (1, C(V, PIQUE)),     # l'adversaire du 2 coupe avec le Valet (maître)
    ],
    atout=PIQUE,
    current_player=2,
)
check("R2.2 precision - adversaire coupe au Valet, que des atouts faibles -> defausse libre",
      same(legal, [C(H8, PIQUE), C(AS, TREFLE)]))


# ===========================================================================
# RÈGLE 3 — conduit à jouer atout -> monter si possible
# ===========================================================================

# 3a. Coupe : un adversaire a coupé avec le 8 d'atout ; on possède le 9 (plus
#     fort) et le 7 (plus faible) -> on DOIT jouer le 9 (surcouper).
legal = legal_cards(
    hand=[C(N9, PIQUE), C(S7, PIQUE)],
    plays_so_far=[
        (3, C(AS, COEUR)),
        (0, C(D10, COEUR)),
        (1, C(H8, PIQUE)),    # adversaire du 2 coupe
    ],
    atout=PIQUE,
    current_player=2,
)
check("R3 - surcouper un adversaire qui a coupe (8) avec le 9",
      same(legal, [C(N9, PIQUE)]))

# 3b. Atout demandé à l'entame : le leader joue la Dame d'atout ; on a le 9
#     (plus fort) et le 8 (plus faible) -> on DOIT jouer le 9.
legal = legal_cards(
    hand=[C(N9, PIQUE), C(H8, PIQUE)],
    plays_so_far=[(3, C(D, PIQUE))],   # entame à l'atout (Dame)
    atout=PIQUE,
    current_player=0,
)
check("R3 - atout demande a l'entame -> monter (9 au-dessus de la Dame)",
      same(legal, [C(N9, PIQUE)]))

# 3c. Atout demandé à l'entame avec le Valet (atout le plus fort) : impossible
#     de monter -> on peut jouer n'importe quel atout (plus faible autorisé).
legal = legal_cards(
    hand=[C(N9, PIQUE), C(H8, PIQUE)],
    plays_so_far=[(3, C(V, PIQUE))],
    atout=PIQUE,
    current_player=0,
)
check("R3 - atout demande, impossible de monter sur le Valet -> atout plus faible permis",
      same(legal, [C(N9, PIQUE), C(H8, PIQUE)]))


# ===========================================================================
# RÈGLE 4 — partenaire maître APRÈS COUPE + que de l'atout -> atout plus
#          faible autorisé (SEUL cas de figure)
# ===========================================================================

# 4a. CAS DISCRIMINANT. Ordre : 3 (entame Coeur) -> 0 (coupe) -> 1 (défausse)
#     -> 2 (nous). Notre partenaire le 0 a coupé avec le 8 d'atout et tient le
#     pli. Nous n'avons que de l'atout : le Valet (plus fort que le 8) et le 7
#     (plus faible). La règle 4 interdit de NOUS FORCER à monter : on a le droit
#     de jouer le 7, même si on possède le Valet.
#     Si seule la règle 3 s'appliquait, le 7 serait illégal et seul le Valet
#     serait autorisé : ceci prouve que la règle 4 est bien implémentée.
legal = legal_cards(
    hand=[C(V, PIQUE), C(S7, PIQUE)],
    plays_so_far=[
        (3, C(AS, COEUR)),    # entame Coeur (adversaire)
        (0, C(H8, PIQUE)),    # notre partenaire coupe et devient maître
        (1, C(S7, TREFLE)),   # l'adversaire se défausse
    ],
    atout=PIQUE,
    current_player=2,
)
check("R4 - partenaire coupe, que de l'atout -> on peut jouer un atout PLUS FAIBLE",
      C(S7, PIQUE) in legal)
check("R4 - ... et aussi l'atout plus fort (liberté totale, pas obligation)",
      same(legal, [C(V, PIQUE), C(S7, PIQUE)]))

# 4b. Même situation mais le partenaire a coupé avec le Valet (atout maître
#     absolu) et nous n'avons que des atouts faibles (7 et 8) -> tout est permis.
legal = legal_cards(
    hand=[C(S7, PIQUE), C(H8, PIQUE)],
    plays_so_far=[
        (3, C(AS, COEUR)),
        (0, C(V, PIQUE)),
        (1, C(S7, TREFLE)),
    ],
    atout=PIQUE,
    current_player=2,
)
check("R4 - partenaire coupe au Valet, atouts faibles -> main entiere",
      same(legal, [C(S7, PIQUE), C(H8, PIQUE)]))

# 4c. CONTRE-ÉPREUVE : « c'est le SEUL cas ». Ici l'ATOUT est demandé à
#     l'entame (ce n'est donc pas une coupe) et notre partenaire est maître
#     avec le 8 d'atout. On possède le 9 (plus fort) et le 7 (plus faible) :
#     la règle 3 s'applique, on DOIT monter avec le 9 et le 7 est interdit.
legal = legal_cards(
    hand=[C(N9, PIQUE), C(S7, PIQUE)],
    plays_so_far=[
        (3, C(S7, PIQUE)),   # entame à l'atout (7)
        (0, C(H8, PIQUE)),   # notre partenaire monte et est maître
        (1, C(S7, TREFLE)),  # un adversaire se défausse (pas d'atout)
    ],
    atout=PIQUE,
    current_player=2,
)
check("R4 contre-epreuve - atout demande (pas une coupe), partenaire maitre -> on DOIT monter",
      same(legal, [C(N9, PIQUE)]))
check("R4 contre-epreuve - l'atout plus faible (7) est bien interdit ici",
      C(S7, PIQUE) not in legal)

# 4d. CONTRE-ÉPREUVE : si notre partenaire n'est PAS maître (c'est un adversaire
#     qui tient le pli avec un atout), on DOIT monter, la règle 4 ne s'applique pas.
legal = legal_cards(
    hand=[C(V, PIQUE), C(S7, PIQUE)],
    plays_so_far=[
        (3, C(AS, COEUR)),
        (0, C(D10, COEUR)),   # notre partenaire fournit sans couper
        (1, C(H8, PIQUE)),    # l'ADVERSAIRE coupe et tient le pli
    ],
    atout=PIQUE,
    current_player=2,
)
check("R4 contre-epreuve - adversaire tient le pli -> on DOIT surcouper (Valet seul)",
      same(legal, [C(V, PIQUE)]))


# ===========================================================================
# TEST D'INTÉGRATION — un pli complet joué légalement, remporté par le partenaire
# ===========================================================================

# Même configuration que 4a : on vérifie qu'un pli où le joueur 2 joue un atout
# plus faible (autorisé par la règle 4) est bien un pli valide et que le
# partenaire le remporte.
trick_plays = [
    (3, C(AS, COEUR)),     # entame
    (0, C(H8, PIQUE)),     # partenaire coupe
    (1, C(S7, TREFLE)),    # adversaire défausse
    (2, C(S7, PIQUE)),     # nous : atout plus faible, autorisé par la règle 4
]
check("Integration - le 7 d'atout est legal dans le pli de la regle 4",
      C(S7, PIQUE) in legal_cards(
          hand=[C(V, PIQUE), C(S7, PIQUE)],
          plays_so_far=trick_plays[:3],
          atout=PIQUE,
          current_player=2,
      ))
check("Integration - le partenaire (0) remporte le pli",
      trick_winner(trick_plays, atout=PIQUE) == 0)


print(f"\n{passed} tests reussis, {failed} tests echoues.")
sys.exit(1 if failed else 0)
