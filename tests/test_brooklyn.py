"""Two representative journeys for David's rule-based Brooklyn family."""

import random
import unittest
from unittest.mock import Mock

from belote.bidding import Contract
from belote.bots import create_bot, get_bot_info
from belote.bots.brooklyn import BrooklynBot
from belote.cards import Card, Rank, Suit
from belote.game import Game
from belote.trick import TrickState, trick_winner
from game_session import GameSession
from rooms import Room


def cards(*codes):
    return [Card(Rank(rank), Suit[suit]) for rank, suit in (code.split("_") for code in codes)]


def contract(team=0):
    return Contract(player=team, team=team, points=80, suit=Suit.PIQUE, is_capot=False)


class BrooklynTests(unittest.TestCase):
    def test_trump_hunt_then_bank_points_with_public_information(self):
        bot = BrooklynBot(0)
        bot.notify_contract(contract())
        hand = cards("V_PIQUE", "9_PIQUE", "A_PIQUE", "7_PIQUE", "A_COEUR", "R_COEUR", "10_TREFLE", "7_CARREAU")
        for expected, others in [
            ("V_PIQUE", cards("R_PIQUE", "D_PIQUE", "10_PIQUE")),
            ("9_PIQUE", cards("8_PIQUE", "7_COEUR", "7_TREFLE")),
        ]:
            trick = TrickState(leader=0, atout=Suit.PIQUE)
            chosen = bot.choose_card(hand, trick, trick.legal_cards_for(hand))
            self.assertEqual(chosen, cards(expected)[0])
            hand.remove(chosen)
            plays = [(0, chosen)] + list(enumerate(others, 1))
            bot.notify_trick_result(plays, trick_winner(plays, Suit.PIQUE))
        # All enemy trumps are out: do not draw partner's remaining trumps.
        lead = TrickState(leader=0, atout=Suit.PIQUE)
        self.assertEqual(bot.choose_card(hand, lead, list(hand)), cards("A_COEUR")[0])

        # Without the jack, draw small rather than sacrifice the nine.
        bot.notify_contract(contract())
        short = cards("9_PIQUE", "R_PIQUE", "7_PIQUE", "A_COEUR")
        self.assertEqual(bot.choose_card(short, lead, short), cards("7_PIQUE")[0])
        # A singleton trump is not automatically hoarded by the attacking team.
        short = cards("7_PIQUE", "A_COEUR")
        self.assertEqual(bot.choose_card(short, lead, short), short[0])

        for team in (0, 1):
            bot.notify_contract(contract(team))
            hand = cards("A_COEUR", "R_COEUR", "7_PIQUE")
            for plays in [list(zip([3], cards("D_COEUR"))),
                          list(zip([1, 2, 3], cards("D_COEUR", "7_COEUR", "8_COEUR")))]:
                trick = TrickState(leader=plays[0][0], atout=Suit.PIQUE, plays=plays)
                self.assertEqual(bot.choose_card(hand, trick, trick.legal_cards_for(hand)), hand[0])
            # Economy is allowed ONLY in attack, last to play, with enemy trumps out.
            bot.played_by_suit[Suit.PIQUE] = set(Rank) - {Rank.SEPT}
            self.assertEqual(bot.choose_card(hand, trick, trick.legal_cards_for(hand)),
                             cards("R_COEUR" if team == 0 else "A_COEUR")[0])

        bot.notify_contract(contract(1))  # Defence cashes side aces, not a trump hunt.
        hand = cards("V_PIQUE", "9_PIQUE", "A_COEUR", "R_COEUR")
        self.assertEqual(bot.choose_card(hand, lead, hand), cards("A_COEUR")[0])
        plays = list(zip([0, 1, 2, 3], cards("R_COEUR", "A_COEUR", "7_COEUR", "8_COEUR")))
        bot.notify_trick_result(plays, 1)
        self.assertTrue(all(Suit.PIQUE not in suits for suits in bot.void_suits.values()))
        # Discarding on a winning partner does not prove a lack of trump either.
        bot.notify_contract(contract())
        plays = list(zip([0, 1, 2, 3], cards("A_COEUR", "7_TREFLE", "8_TREFLE", "9_TREFLE")))
        bot.notify_trick_result(plays, 0)
        self.assertIn(Suit.PIQUE, bot.void_suits[1])
        self.assertNotIn(Suit.PIQUE, bot.void_suits[2])
        # Load partner's safe ace, rather than discard a worthless card.
        bot.notify_contract(contract())
        hand = cards("10_COEUR", "7_COEUR")
        trick = TrickState(leader=2, atout=Suit.PIQUE,
                           plays=list(zip([2, 3], cards("A_COEUR", "R_COEUR"))))
        self.assertEqual(bot.choose_card(hand, trick, trick.legal_cards_for(hand)), hand[0])

    def test_catalog_and_complete_seeded_games(self):
        info = get_bot_info("brooklyn_v1")
        self.assertEqual((info["family"], info["author"]), ("Brooklyn", "David"))
        self.assertEqual(len(set(info["names"])), 4)
        for seed in range(4):
            players = {seat: create_bot("brooklyn_v1", seat) for seat in range(4)}
            self.assertTrue(all(isinstance(bot, BrooklynBot) for bot in players.values()))
            game = Game(players, target_score=300, first_dealer=seed, rng=random.Random(seed))
            self.assertIn(game.play_until_end(), (0, 1))
            # The same public notifications must reach bots in the web engine,
            # including automatic last tricks, claims and the next deal's reset.
            session = GameSession(Room("TEST"), target_score=300,
                                  bot_ids={seat: "brooklyn_v1" for seat in range(4)})
            session.game.dealer = seed
            session.game.rng = random.Random(seed)
            session.sleep = Mock()
            session.broadcast = Mock()
            for bot in session.players.values():
                bot.notify_contract = Mock(wraps=bot.notify_contract)
                bot.notify_trick_result = Mock(wraps=bot.notify_trick_result)
            session.run()
            accepted = sum(not log.annulee for log in session.game.donne_logs)
            for bot in session.players.values():
                self.assertEqual(bot.notify_contract.call_count, accepted)
                self.assertEqual(bot.notify_trick_result.call_count, accepted * 8)
                self.assertEqual(bot.tricks_played, 8)
                self.assertEqual(bot.is_preneur, bot.player_id % 2 == session.game.donne_logs[-1].contract.team)
            self.assertEqual(session.game.donne_logs, game.donne_logs)
            self.assertEqual(session.game.cumulative_scores, game.cumulative_scores)
            self.assertEqual(session.winner_team, game.winner_team)
            for log in game.donne_logs:
                if log.annulee:
                    continue
                hands = {p: list(h) for p, h in log.initial_hands.items()}
                leader = (log.dealer - 1) % 4
                self.assertEqual(len(log.tricks), 8)
                for plays, winner in zip(log.tricks, log.trick_winners):
                    trick = TrickState(leader, log.contract.suit)
                    for seat, card in plays:
                        self.assertEqual(seat, trick.current_player)
                        self.assertIn(card, trick.legal_cards_for(hands[seat]))
                        hands[seat].remove(card)
                        trick.play(seat, card)
                    self.assertEqual(trick.winner(), winner)
                    leader = winner
                self.assertTrue(all(not hand for hand in hands.values()))


if __name__ == "__main__":
    unittest.main()
