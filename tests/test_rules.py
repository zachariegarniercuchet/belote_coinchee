"""
Suite de tests manuelle (sans dépendance externe) pour vérifier les points
les plus subtils des règles : cartes jouables, belote, et calcul du score.

Lancer avec : python3 tests/test_rules.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belote.cards import Card, Rank, Suit
from belote.trick import legal_cards, trick_winner
from belote.bidding import Contract, CoincheState
from belote.scoring import compute_donne_score, find_belote_holder, round_to_nearest_ten

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


# --- 1. Doit fournir la couleur demandée si possible ---
hand = [C(AS, COEUR), C(V, PIQUE)]
plays = [(0, C(D10, COEUR))]
legal = legal_cards(hand, plays, atout=PIQUE, current_player=1)
check("fournir la couleur demandee", legal == [C(AS, COEUR)])

# --- 2. Pas de couleur demandée, partenaire maître -> défausse libre ---
hand = [C(AS, TREFLE), C(V, PIQUE)]
plays = [(0, C(AS, COEUR)), (3, C(D10, COEUR))]  # joueur 0 (partenaire de 2) est maître
legal = legal_cards(hand, plays, atout=PIQUE, current_player=2)
check("partenaire maitre -> defausse libre", set(legal) == {C(AS, TREFLE), C(V, PIQUE)})

# --- 3. Pas de couleur demandée, adversaire maître, doit couper si possible ---
hand = [C(AS, TREFLE), C(N9, PIQUE), C(H8, PIQUE)]
plays = [(0, C(AS, COEUR))]  # joueur 0 (adversaire de 1) est maître
legal = legal_cards(hand, plays, atout=PIQUE, current_player=1)
check("doit couper si adversaire maitre", set(legal) == {C(N9, PIQUE), C(H8, PIQUE)})

# --- 4. Doit monter (surcouper) si un adversaire a déjà coupé ---
hand = [C(V, PIQUE), C(H8, PIQUE)]
plays = [(0, C(AS, COEUR)), (1, C(H8, PIQUE))]  # joueur 1 (adversaire de 2) a coupé avec 8 pique
legal = legal_cards(hand, plays, atout=PIQUE, current_player=2)
check("doit monter sur l'adversaire qui a coupe", legal == [C(V, PIQUE)])

# --- 5. "Ne pas pisser" : que des atouts plus faibles -> défausse libre ---
hand = [C(H8, PIQUE), C(AS, TREFLE)]
plays = [(0, C(AS, COEUR)), (1, C(V, PIQUE))]  # joueur 1 a coupe avec le valet (le plus fort atout)
legal = legal_cards(hand, plays, atout=PIQUE, current_player=2)
check("ne pas pisser -> defausse libre malgre avoir de l'atout", set(legal) == {C(H8, PIQUE), C(AS, TREFLE)})

# --- 6. Entame à l'atout : doit fournir atout et monter si possible ---
hand = [C(N9, PIQUE), C(H8, PIQUE)]
plays = [(0, C(D, PIQUE))]
legal = legal_cards(hand, plays, atout=PIQUE, current_player=1)
check("entame atout -> doit monter (9 bat dame)", legal == [C(N9, PIQUE)])

# --- 7. Belote : détection du joueur avec Roi+Dame d'atout ---
hands = {
    0: [C(R, PIQUE), C(D, PIQUE)] + [C(S7, COEUR)] * 0,
    1: [],
    2: [],
    3: [],
}
holder = find_belote_holder(hands, PIQUE)
check("belote detectee pour le bon joueur", holder == 0)
holder2 = find_belote_holder(hands, COEUR)
check("pas de belote si mauvaise couleur d'atout", holder2 is None)

# --- 8. Arrondi a la dizaine ---
check("arrondi 85 -> 90", round_to_nearest_ten(85) == 90)
check("arrondi 84 -> 80", round_to_nearest_ten(84) == 80)
check("arrondi 80 -> 80", round_to_nearest_ten(80) == 80)

# --- 9. Score : contrat reussi simple, sans coinche ---
contract = Contract(player=0, team=0, points=90, suit=PIQUE, is_capot=False)
result = compute_donne_score(
    contract=contract,
    trick_points={0: 100, 1: 52},
    last_trick_winner=0,  # equipe 0
    capot_team=None,
    belote_team=None,
)
# preneurs (equipe 0): 100 + 10 (dix de der) = 110 total, + 90 (contrat) = 200
# defense (equipe 1): 52
check("contrat reussi - preneurs", result.final_scores[0] == 200)
check("contrat reussi - defense", result.final_scores[1] == 50)

# --- 10. Score : chute, sans coinche ---
contract2 = Contract(player=0, team=0, points=100, suit=PIQUE, is_capot=False)
result2 = compute_donne_score(
    contract=contract2,
    trick_points={0: 60, 1: 92},
    last_trick_winner=1,
    capot_team=None,
    belote_team=None,
)
# preneurs echouent (60 < 100) -> 0 points (pas de belote)
# defense: 160 (chute) + 100 (contrat) = 260 -> arrondi 260
check("chute - preneurs", result2.final_scores[0] == 0)
check("chute - defense", result2.final_scores[1] == 260)

# --- 11. Score : contrat coinche et reussi ---
contract3 = Contract(player=0, team=0, points=90, suit=PIQUE, is_capot=False,
                      coinche_state=CoincheState.COINCHE, coinche_by_team=1)
result3 = compute_donne_score(
    contract=contract3,
    trick_points={0: 100, 1: 52},
    last_trick_winner=0,
    capot_team=None,
    belote_team=None,
)
# preneurs: (160 + 0 + 90) * 2 = 500
check("coinche reussi - preneurs", result3.final_scores[0] == 500)
check("coinche reussi - defense (rien sauf belote)", result3.final_scores[1] == 0)

# --- 12. Score : capot demande et reussi ---
contract4 = Contract(player=0, team=0, points=None, suit=PIQUE, is_capot=True)
result4 = compute_donne_score(
    contract=contract4,
    trick_points={0: 152, 1: 0},
    last_trick_winner=0,
    capot_team=0,
    belote_team=None,
)
# preneurs: 152 + 100 (dix de der capot) = 252, + 250 (contrat capot) = 502
check("capot demande reussi", result4.final_scores[0] == 500)  # 502 arrondi -> 500

print(f"\n{passed} tests reussis, {failed} tests echoues.")
sys.exit(1 if failed else 0)
