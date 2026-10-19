"""Tablage : détection, garantie des plis et équivalence des scores console/web.

python -B -m unittest discover -s tests -p test_claim.py
"""

import copy
import random
import unittest
from unittest.mock import Mock, patch

from belote.bidding import ActionType
from belote.cards import Card, Rank, Suit, full_deck
from belote.claim import find_claim, play_claim
from belote.game import Donne
from belote.player import Player
from belote.trick import TrickState
from game_session import GameSession, TRICK_COLLECT_PAUSE_RANGE
from rooms import Room


def hand(*codes):
    return [Card(Rank(rank), Suit[suit]) for rank, suit in (code.split("_") for code in codes)]


TRUMPS = {
    0: hand("A_COEUR", "10_COEUR"),
    1: hand("7_PIQUE", "8_PIQUE"),
    2: hand("R_COEUR", "D_CARREAU"),
    3: hand("V_COEUR", "A_TREFLE"),
}
MASTERS = {
    0: hand("A_COEUR", "10_COEUR"),
    1: hand("R_COEUR", "D_COEUR"),
    2: hand("V_COEUR", "A_CARREAU"),
    3: hand("7_COEUR", "A_TREFLE"),
}


class FirstLegalPlayer(Player):
    def choose_bid(self, hand, state, legal):
        wanted = ActionType.ENCHERE if state.contract is None else ActionType.PASSE
        return next(action for action in legal if action.type == wanted)

    def choose_card(self, hand, state, legal):
        return legal[0]


class ClaimDetectionTests(unittest.TestCase):
    def test_only_trumps_in_one_hand_regardless_of_leader(self):
        for leader in range(4):
            with self.subTest(leader=leader):
                claim = find_claim(TRUMPS, leader, Suit.PIQUE)
                self.assertEqual((claim.seat, claim.reason), (1, "trumps"))

    def test_someone_else_still_has_trump(self):
        hands = copy.deepcopy(TRUMPS)
        hands[0][0] = Card(Rank.VALET, Suit.PIQUE)
        self.assertIsNone(find_claim(hands, 1, Suit.PIQUE))

    def test_trump_holder_also_has_side_suit(self):
        hands = copy.deepcopy(TRUMPS)
        hands[1][0] = Card(Rank.SEPT, Suit.TREFLE)
        self.assertIsNone(find_claim(hands, 1, Suit.PIQUE))

    def test_all_remaining_cards_are_masters(self):
        claim = find_claim(MASTERS, 0, Suit.PIQUE)
        self.assertEqual((claim.seat, claim.reason), (0, "masters"))

    def test_masters_in_multiple_suits(self):
        hands = copy.deepcopy(MASTERS)
        hands[0][1] = Card(Rank.DIX, Suit.CARREAU)
        hands[2][1] = Card(Rank.ROI, Suit.CARREAU)
        self.assertEqual(find_claim(hands, 0, Suit.PIQUE).seat, 0)

    def test_played_honors_no_longer_count(self):
        hands = {
            0: hand("9_COEUR", "8_COEUR"),
            1: hand("7_COEUR", "7_CARREAU"),
            2: hand("8_CARREAU", "7_TREFLE"),
            3: hand("9_CARREAU", "8_TREFLE"),
        }
        self.assertEqual(find_claim(hands, 0, Suit.PIQUE).reason, "masters")

    def test_holding_ace_and_loser_is_not_enough(self):
        hands = copy.deepcopy(MASTERS)
        hands[0][1] = Card(Rank.HUIT, Suit.COEUR)
        self.assertIsNone(find_claim(hands, 0, Suit.PIQUE))

    def test_masters_without_the_lead_cannot_claim(self):
        self.assertIsNone(find_claim(MASTERS, 1, Suit.PIQUE))

    def test_masters_with_trump_elsewhere_cannot_claim(self):
        hands = copy.deepcopy(MASTERS)
        hands[1][1] = Card(Rank.SEPT, Suit.PIQUE)
        self.assertIsNone(find_claim(hands, 0, Suit.PIQUE))

    def test_empty_hands_last_trick_and_mid_trick_do_not_claim(self):
        self.assertIsNone(find_claim({seat: [] for seat in range(4)}, 0, Suit.PIQUE))
        for remaining in (TRUMPS, MASTERS):
            last_cards = {seat: cards[:1] for seat, cards in remaining.items()}
            for leader in range(4):
                self.assertIsNone(find_claim(last_cards, leader, Suit.PIQUE))
        hands = copy.deepcopy(TRUMPS)
        hands[0].pop()
        self.assertIsNone(find_claim(hands, 1, Suit.PIQUE))

    def test_every_legal_order_wins_all_claimed_tricks(self):
        # Explore toutes les suites de cartes légales, pas seulement le jeu
        # déterministe utilisé pour enregistrer les plis après le tablage.
        def visit(hands, trick, winner):
            seat = trick.current_player
            for card in trick.legal_cards_for(hands[seat]):
                remaining = {p: list(cards) for p, cards in hands.items()}
                remaining[seat].remove(card)
                next_trick = TrickState(trick.leader, trick.atout, trick.plays + [(seat, card)])
                if next_trick.is_complete:
                    self.assertEqual(next_trick.winner(), winner)
                    if remaining[winner]:
                        visit(remaining, TrickState(winner, trick.atout), winner)
                else:
                    visit(remaining, next_trick, winner)

        for hands, leaders in ((TRUMPS, range(4)), (MASTERS, [0])):
            for leader in leaders:
                with self.subTest(leader=leader, hands=hands):
                    claim = find_claim(hands, leader, Suit.PIQUE)
                    visit(hands, TrickState(leader, Suit.PIQUE), claim.seat)

    def test_resolution_keeps_hands_and_records_all_cards(self):
        original = copy.deepcopy(TRUMPS)
        claim = find_claim(TRUMPS, 0, Suit.PIQUE)
        tricks = play_claim(TRUMPS, 0, Suit.PIQUE, claim)
        self.assertEqual(TRUMPS, original)
        self.assertEqual([trick.winner() for trick in tricks], [1, 1])
        self.assertEqual(len({card for trick in tricks for _, card in trick.plays}), 8)


class ClaimGameTests(unittest.TestCase):
    def test_claim_from_first_trick_preserves_capot_and_belote(self):
        suits = (Suit.COEUR, Suit.PIQUE, Suit.CARREAU, Suit.TREFLE)
        hands = {seat: [card for card in full_deck() if card.suit == suit]
                 for seat, suit in enumerate(suits)}
        players = {seat: FirstLegalPlayer(seat, str(seat)) for seat in range(4)}
        with patch("belote.game.deal", side_effect=lambda *_: copy.deepcopy(hands)):
            with patch("belote.game.find_claim", return_value=None):
                reference = Donne(players, dealer=0, rng=random.Random(0)).play()
            console = Donne(players, dealer=0, rng=random.Random(0)).play()
        session = GameSession(Room("TEST"), target_score=1000)
        session.game.players = players
        session.game.dealer = 0
        session.sleep = Mock()
        session.broadcast = Mock()
        with patch("game_session.deal", side_effect=lambda *_: copy.deepcopy(hands)):
            web = session.game.play_one_donne()
        for log in (console, web):
            self.assertEqual(log.claim.seat, 1)
            self.assertEqual(log.trick_winners, [1] * 8)
            self.assertEqual(log.result, reference.result)
            self.assertEqual(log.result.capot_team, 1)
            self.assertEqual(log.result.belote_team, 1)
            self.assertEqual(log.result.dix_de_der_team, 1)
        self.assertEqual(session.ctx.claim["remaining_tricks"], 8)

    def test_console_and_web_keep_scores_and_history(self):
        claim_count = 0
        belote_count = 0
        hidden_belote_count = 0
        for seed in range(12):
            players = {seat: FirstLegalPlayer(seat, f"Joueur {seat}") for seat in range(4)}
            with patch("belote.game.find_claim", return_value=None):
                reference = Donne(players, dealer=0, rng=random.Random(seed)).play()
            console = Donne(players, dealer=0, rng=random.Random(seed)).play()
            room = Room("TEST")
            session = GameSession(room, target_score=1000)
            session.game.players = players
            session.game.dealer = 0
            session.game.rng = random.Random(seed)
            session.sleep = Mock()
            broadcasts = []
            session.broadcast = lambda: broadcasts.append(copy.deepcopy(session._build_common()))
            web = session.game.play_one_donne()
            for log in (console, web):
                with self.subTest(seed=seed, web=log is web):
                    self.assertEqual(log.result, reference.result)
                    self.assertEqual(log.tricks, reference.tricks)
                    self.assertEqual(log.trick_winners, reference.trick_winners)
                    self.assertEqual(len(log.tricks), 8)
            live_tricks = web.tricks[:8 - session.ctx.claim["remaining_tricks"]] if web.claim else web.tricks
            holder = session.ctx.belote_holder_seat
            played_pair = [card for trick in live_tricks for seat, card in trick
                           if seat == holder and card.suit == web.contract.suit
                           and card.rank in (Rank.ROI, Rank.DAME)]
            announcements = session._build_common()["belote_announcements"]
            self.assertEqual([entry["label"] for entry in announcements],
                             ["Belote !", "Rebelote !"][:len(played_pair)])
            self.assertEqual([entry["card_id"] for entry in announcements],
                             [f"{card.rank.name}_{card.suit.name}" for card in played_pair])
            self.assertTrue(all(entry["seat"] == holder for entry in announcements))
            # Ni le plateau ni les joueurs ne doivent connaître la paire avant
            # sa première carte annoncée. Le score final reste inchangé.
            for state in broadcasts:
                visible = bool(state["belote_announcements"]) or state["last_donne_result"] is not None
                self.assertEqual(state["belote_holder_seat"], holder if visible else None)
                self.assertEqual(state["belote_team"], session.ctx.belote_team if visible else None)
                if holder is not None and state["phase"] == "trick" and not visible:
                    hidden_belote_count += 1
                    for seat in range(4):
                        private = session._build_for_player(state, seat)
                        self.assertIsNone(private["belote_team"])
                        self.assertIsNone(private["belote_holder_seat"])
            belote_count += len(announcements)
            if web.claim:
                claim_count += 1
                revealed = session._build_common()["claim"]
                self.assertGreater(revealed["remaining_tricks"], 1)
                self.assertEqual(revealed["seat"], web.claim.seat)
                self.assertEqual(len(revealed["hands"]), 4)
                self.assertEqual(
                    sum(map(len, revealed["hands"].values())), 4 * revealed["remaining_tricks"],
                )
                self.assertTrue(all(state["claim"] is None for state in broadcasts[:-1]))
            else:
                # Le dernier pli arrive en une seule mise à jour, sans mains
                # partiellement vidées ni demande de choix pour la dernière carte.
                self.assertFalse(any(0 < sum(state["hand_counts"].values()) < 4
                                     for state in broadcasts))
                self.assertTrue(any(len(state["completed_trick"]) == 4
                                    and sum(state["hand_counts"].values()) == 0
                                    and state["waiting_seat"] is None
                                    for state in broadcasts))
                self.assertGreaterEqual(session.sleep.call_args_list[-1].args[0],
                                        TRICK_COLLECT_PAUSE_RANGE[0] + 1.0)
            self.assertEqual(sum(session.ctx.tricks_won_this_donne.values()), 8)
            self.assertTrue(all(not hand for hand in session.ctx.hands.values()))
        self.assertGreater(claim_count, 0)
        self.assertGreater(belote_count, 0)
        self.assertGreater(hidden_belote_count, 0)

    def test_session_clears_claim_and_keeps_final_recap(self):
        room = Room("TEST")
        session = GameSession(room, target_score=5000)
        session.game.players = {seat: FirstLegalPlayer(seat, str(seat)) for seat in range(4)}
        session.game.rng = random.Random(0)
        session.sleep = Mock()
        session.broadcast = Mock()
        session.game.play_one_donne()
        session.ctx.claim = {"seat": 0, "hands": {"0": ["ancienne main"]}}
        session.ctx.belote_announcements = [{"seat": 0, "label": "Rebelote !"}]
        states = []
        session.broadcast = lambda: states.append(copy.deepcopy(session._build_common()))
        session.game.play_one_donne()
        self.assertIsNone(states[0]["claim"])
        self.assertEqual(states[0]["belote_announcements"], [])

        session.game.target_score = 100
        wait_for_recap = session._wait_for_recap
        def read_recap():
            self.assertFalse(session.finished)
            self.assertEqual(states[-1]["phase"], "donne_end")
            self.assertFalse(states[-1]["game_over"])
            self.assertIsNotNone(states[-1]["last_donne_result"])
            self.assertFalse(session.game.finished)
            self.assertFalse(states[-1]["final_donne"])
            wait_for_recap()

        session._wait_for_recap = Mock(side_effect=read_recap)
        states.clear()
        session.run()
        final_recap = states[-2]
        self.assertEqual(final_recap["phase"], "donne_end")
        self.assertTrue(final_recap["final_donne"])
        self.assertFalse(final_recap["game_over"])
        self.assertEqual(final_recap["winner_team"], session.game.winner_team)
        self.assertEqual(final_recap["last_donne_result"], states[-1]["last_donne_result"])
        self.assertEqual(final_recap["score_history"], states[-1]["score_history"])
        intermediate_recaps = [state for state in states
                               if state["phase"] == "donne_end" and not state["final_donne"]]
        self.assertGreater(len(intermediate_recaps), 0)
        self.assertEqual(session._wait_for_recap.call_count, len(intermediate_recaps))
        self.assertTrue(session.finished)
        self.assertEqual(states[-1]["phase"], "game_end")
        self.assertTrue(states[-1]["game_over"])


if __name__ == "__main__":
    unittest.main()
