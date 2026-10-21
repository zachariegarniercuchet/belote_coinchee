"""Card play, partnership bidding and full-game parity for the Brooklyn family."""

import random
import unittest
from itertools import product
from unittest.mock import Mock

from belote.bidding import ActionType, BidAction, BiddingState, Contract
from belote.bots import create_bot, get_bot_info
from belote.bots.brooklyn import BrooklynBot
from belote.bots.brooklyn_v2 import BrooklynBotV2
from belote.bots.brooklyn_v3 import BrooklynBotV3
from belote.cards import Card, Rank, Suit
from belote.game import Game
from belote.trick import TrickState, trick_winner
from game_session import GameSession
from rooms import Room
from serialize import card_to_dict, sorted_hand


def cards(*codes):
    return [Card(Rank(rank), Suit[suit]) for rank, suit in (code.split("_") for code in codes)]


def contract(team=0):
    return Contract(player=team, team=team, points=80, suit=Suit.PIQUE, is_capot=False)


class BrooklynTests(unittest.TestCase):
    def test_partnership_auction_counts_each_contribution_once(self):
        for opener_hand, support_hand, expected in [
            (cards("V_PIQUE", "R_PIQUE", "D_PIQUE", "7_PIQUE", "10_COEUR", "7_COEUR", "10_TREFLE", "7_TREFLE"),
             cards("9_PIQUE", "A_PIQUE", "A_COEUR", "R_COEUR", "D_COEUR", "D_TREFLE", "V_TREFLE", "9_TREFLE"),
             [100, 120, 140]),
            (cards("V_PIQUE", "9_PIQUE", "R_PIQUE", "D_PIQUE", "7_PIQUE", "A_COEUR", "8_COEUR", "10_COEUR"),
             cards("A_PIQUE", "R_COEUR", "A_TREFLE", "A_CARREAU", "10_TREFLE", "7_TREFLE", "7_CARREAU", "8_CARREAU"),
             [110, 130, 150]),
            # With only three trumps, neither the trump ace nor a void adds credit.
            (cards("V_PIQUE", "9_PIQUE", "A_PIQUE", "A_COEUR", "8_COEUR", "R_TREFLE", "8_TREFLE", "7_COEUR"),
             cards("7_PIQUE", "R_PIQUE", "R_COEUR", "D_COEUR", "A_CARREAU", "R_CARREAU", "A_TREFLE", "V_TREFLE"),
             [90, 110]),
            # Three-trump belote is +10, including in the later total ceiling.
            (cards("V_PIQUE", "R_PIQUE", "D_PIQUE", "A_COEUR", "7_COEUR", "10_TREFLE", "7_TREFLE", "7_CARREAU"),
             cards("9_PIQUE", "A_PIQUE", "A_TREFLE", "A_CARREAU", "R_COEUR", "D_COEUR", "8_TREFLE", "8_CARREAU"),
             [90, 120]),
        ]:
            bots = {seat: BrooklynBotV2(seat) for seat in (0, 2)}
            state = BiddingState(dealer=1)
            hands = {0: opener_hand, 2: support_hand}
            while not state.finished:
                seat = state.current_player
                legal = state.legal_actions()
                if seat in bots:
                    action = bots[seat].choose_bid(hands[seat], state, legal)
                    # Re-reading the same state must not spend a second credit.
                    self.assertEqual(bots[seat].choose_bid(hands[seat], state, legal), action)
                else:
                    if seat == 1 and len(state.history) == 1:
                        # Enemy overcalls must not inflate our card-value credits.
                        action = next(a for a in legal if a.type == ActionType.ENCHERE
                                      and a.suit == Suit.COEUR and a.points == expected[0] + 10)
                    else:
                        action = next(a for a in legal if a.type == ActionType.PASSE)
                self.assertIn(action, legal)
                state.apply(action)
            numeric = [a.points for seat, a in state.history
                       if seat % 2 == 0 and a.type == ActionType.ENCHERE]
            self.assertEqual(numeric, expected)
            self.assertEqual(bots[0].partner_raise_points, expected[1] - expected[0])
            self.assertEqual([r.points for r in bots[0].partner_raises], [expected[1] - expected[0]])
            for bot in bots.values():
                bot.notify_contract(state.contract)
                self.assertTrue(bot.is_attacking)
            # Support observations survive acceptance, then reset for the next deal.
            self.assertTrue(bots[0].partner_raises)
            bots[0].notify_donne_start()
            self.assertEqual(bots[0].partner_raise_points, 0)
            self.assertEqual(bots[0].partner_raises, [])
        for weak_hand in [
            cards("V_PIQUE", "A_PIQUE", "A_COEUR", "10_COEUR", "A_TREFLE", "10_TREFLE", "A_CARREAU", "10_CARREAU"),
            cards("A_PIQUE", "10_PIQUE", "R_PIQUE", "A_COEUR", "R_COEUR", "A_TREFLE", "R_TREFLE", "A_CARREAU"),
            # Three trumps and J/9 are insufficient without side strength.
            cards("V_PIQUE", "9_PIQUE", "7_PIQUE", "R_COEUR", "D_COEUR", "V_TREFLE", "8_TREFLE", "7_CARREAU"),
            cards("9_PIQUE", "8_PIQUE", "7_PIQUE", "10_COEUR", "7_COEUR", "R_TREFLE", "8_TREFLE", "7_CARREAU"),
        ]:
            state = BiddingState(dealer=1)
            self.assertEqual(BrooklynBotV2(0).choose_bid(weak_hand, state, state.legal_actions()).type,
                             ActionType.PASSE)
        # The first side ace qualifies 80; extra aces and J+9 each add 10.
        for hand, amount in [
            (cards("V_PIQUE", "A_PIQUE", "7_PIQUE", "A_COEUR", "10_COEUR", "R_TREFLE", "8_TREFLE", "7_CARREAU"), 80),
            (cards("V_PIQUE", "A_PIQUE", "7_PIQUE", "A_COEUR", "10_COEUR", "A_TREFLE", "8_TREFLE", "7_CARREAU"), 90),
            (cards("V_PIQUE", "9_PIQUE", "7_PIQUE", "A_COEUR", "10_COEUR", "R_TREFLE", "8_TREFLE", "7_CARREAU"), 90),
            (cards("9_PIQUE", "8_PIQUE", "7_PIQUE", "10_COEUR", "7_COEUR", "10_TREFLE", "8_TREFLE", "7_CARREAU"), 80),
        ]:
            state = BiddingState(dealer=1)
            self.assertEqual(BrooklynBotV2(0).choose_bid(hand, state, state.legal_actions()),
                             BidAction.enchere(amount, Suit.PIQUE))

        # Initial overcalls now include extra aces, not just the trump description.
        state = BiddingState(dealer=0)  # seat 3 opens, then Brooklyn at seat 0
        state.apply(next(a for a in state.legal_actions() if a.type == ActionType.ENCHERE
                         and a.suit == Suit.CARREAU and a.points == 90))
        hand = cards("V_PIQUE", "9_PIQUE", "7_PIQUE", "A_COEUR", "8_COEUR", "A_TREFLE", "8_TREFLE", "7_CARREAU")
        self.assertEqual(BrooklynBotV2(0).choose_bid(hand, state, state.legal_actions()),
                         BidAction.enchere(100, Suit.PIQUE))

        # A stronger independent suit can replace the team's earlier proposal.
        # Old support must not be carried across the switch or charged twice.
        state = BiddingState(dealer=3)
        for action in (BidAction.enchere(80, Suit.COEUR), BidAction.passe(),
                       BidAction.enchere(90, Suit.COEUR), BidAction.enchere(100, Suit.CARREAU)):
            state.apply(action)
        partner = BrooklynBotV2(2)
        support_hand = cards("A_PIQUE", "R_PIQUE", "V_COEUR", "R_COEUR", "D_COEUR", "7_TREFLE", "9_TREFLE", "7_CARREAU")
        state.apply(partner.choose_bid(support_hand, state, state.legal_actions()))
        self.assertEqual(partner.partner_raise_points, 10)
        state.apply(BidAction.passe())
        hand = cards("V_PIQUE", "9_PIQUE", "7_PIQUE", "A_COEUR", "8_COEUR", "A_TREFLE", "8_TREFLE", "A_CARREAU")
        switch = BrooklynBotV2(0).choose_bid(hand, state, state.legal_actions())
        self.assertEqual(switch, BidAction.enchere(110, Suit.PIQUE))
        state.apply(switch)
        state.apply(BidAction.passe())
        self.assertEqual(partner.choose_bid(support_hand, state, state.legal_actions()), BidAction.passe())
        self.assertEqual(partner.partner_raise_points, 0)
        self.assertEqual(partner.partner_raises, [])

        # Hybrid v3 opens on v1's valuation, including a hand v2 rejects.
        # Then each partner's J/9, side aces and two-trump belote count once.
        for opener_hand, support_hand, expected in [
            (cards("A_PIQUE", "10_PIQUE", "R_PIQUE", "A_COEUR", "R_COEUR", "A_TREFLE", "R_TREFLE", "A_CARREAU"),
             cards("V_PIQUE", "9_PIQUE", "D_PIQUE", "7_PIQUE", "7_COEUR", "8_COEUR", "7_TREFLE", "7_CARREAU"),
             [90, 110]),
            (cards("V_PIQUE", "9_PIQUE", "A_PIQUE", "7_PIQUE", "A_COEUR", "R_COEUR", "10_TREFLE", "7_CARREAU"),
             cards("R_PIQUE", "D_PIQUE", "A_TREFLE", "7_TREFLE", "A_CARREAU", "8_CARREAU", "7_COEUR", "8_COEUR"),
             [120, 160]),
        ]:
            state = BiddingState(dealer=1)
            bots = {seat: BrooklynBotV3(seat) for seat in (0, 2)}
            hands = {0: opener_hand, 2: support_hand}
            self.assertEqual(BrooklynBot(0).choose_bid(opener_hand, state, state.legal_actions()),
                             BidAction.enchere(expected[0], Suit.PIQUE))
            while not state.finished:
                seat = state.current_player
                legal = state.legal_actions()
                if seat in bots:
                    action = bots[seat].choose_bid(hands[seat], state, legal)
                    self.assertEqual(bots[seat].choose_bid(hands[seat], state, legal), action)
                elif seat == 1 and len(state.history) == 1:
                    action = BidAction.enchere(expected[0] + 10, Suit.COEUR)
                else:
                    action = BidAction.passe()
                self.assertIn(action, legal)
                state.apply(action)
            self.assertEqual([a.points for seat, a in state.history
                              if seat % 2 == 0 and a.type == ActionType.ENCHERE], expected)
            self.assertEqual(bots[0].partner_raise_points, expected[1] - expected[0])
            bots[0].notify_donne_start()
            self.assertEqual(bots[0].partner_raises, [])

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
            # Last seat still cashes the highest winner with all enemy trumps out.
            bot.played_by_suit[Suit.PIQUE] = set(Rank) - {Rank.SEPT}
            self.assertEqual(bot.choose_card(hand, trick, trick.legal_cards_for(hand)),
                             cards("A_COEUR")[0])

        for bot_class in (BrooklynBot, BrooklynBotV2, BrooklynBotV3):
            for team in (0, 1):
                for last, ace_out, expected in [
                    (False, False, "R_COEUR"),
                    (False, True, "10_COEUR"),
                    (True, False, "10_COEUR"),
                    (True, True, "10_COEUR"),
                ]:
                    taker = bot_class(0)
                    taker.notify_contract(contract(team))
                    hand = cards("10_COEUR", "R_COEUR", "7_PIQUE")
                    if ace_out:
                        taker.played_by_suit[Suit.COEUR].add(Rank.AS)
                    plays = (list(zip([1, 2, 3], cards("D_COEUR", "7_COEUR", "8_COEUR"))) if last
                             else list(zip([2, 3], cards("7_COEUR", "D_COEUR"))))
                    trick = TrickState(leader=plays[0][0], atout=Suit.PIQUE, plays=plays)
                    self.assertEqual(taker.choose_card(hand, trick, trick.legal_cards_for(hand)), cards(expected)[0])

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

        # Charge likely-lost points, not a future ace, onto partner's trump.
        # A-10 and a publicly endangered late ace are the deliberate exceptions.
        for bot_class in (BrooklynBot, BrooklynBotV2, BrooklynBotV3):
            for hand, expected, late_cut_risk in [
                (cards("A_COEUR", "10_TREFLE", "R_CARREAU", "7_CARREAU"), "10_TREFLE", False),
                (cards("A_COEUR", "R_COEUR", "7_TREFLE"), "R_COEUR", False),
                (cards("A_COEUR", "7_TREFLE", "8_CARREAU"), "7_TREFLE", False),
                (cards("A_COEUR", "10_COEUR", "7_CARREAU"), "A_COEUR", False),
                (cards("A_COEUR", "7_TREFLE"), "7_TREFLE", False),
                (cards("A_COEUR", "7_TREFLE"), "A_COEUR", True),
                (cards("A_COEUR", "R_TREFLE", "8_CARREAU"), "R_TREFLE", True),
                (cards("A_COEUR", "9_PIQUE"), "9_PIQUE", False),
                (cards("A_COEUR"), "A_COEUR", False),
            ]:
                feeder = bot_class(0)
                feeder.notify_contract(contract())
                if late_cut_risk:
                    # Seat 1 discards on partner 3, proving hearts void but NOT
                    # trump void. Our heart ace may be cut if kept for later.
                    history = list(zip([3, 0, 1, 2], cards("10_COEUR", "8_COEUR", "7_CARREAU", "D_COEUR")))
                    feeder.notify_trick_result(history, 3)
                trick = TrickState(leader=2, atout=Suit.PIQUE,
                                   plays=list(zip([2, 3], cards("V_PIQUE", "7_PIQUE"))))
                if any(c.suit == Suit.PIQUE for c in hand):
                    # Void in diamonds with partner master: both the trump and
                    # ace are legal, so this really tests the non-ace fallback.
                    trick = TrickState(leader=1, atout=Suit.PIQUE,
                                       plays=list(zip([1, 2, 3], cards("8_CARREAU", "V_PIQUE", "9_CARREAU"))))
                self.assertEqual(feeder.choose_card(hand, trick, trick.legal_cards_for(hand)), cards(expected)[0])

    def test_catalog_and_complete_seeded_games(self):
        info = get_bot_info("brooklyn_v1")
        self.assertEqual((info["family"], info["author"]), ("Brooklyn", "David"))
        self.assertEqual(len(set(info["names"])), 4)
        for bot_id, seed in product(("brooklyn_v1", "brooklyn_v2", "brooklyn_v3"), range(4)):
            players = {seat: create_bot(bot_id, seat) for seat in range(4)}
            self.assertTrue(all(isinstance(bot, BrooklynBot) for bot in players.values()))
            game = Game(players, target_score=300, first_dealer=seed, rng=random.Random(seed))
            self.assertIn(game.play_until_end(), (0, 1))
            # The same public notifications must reach bots in the web engine,
            # including automatic last tricks, claims and the next deal's reset.
            session = GameSession(Room("TEST"), target_score=300,
                                  bot_ids={seat: bot_id for seat in range(4)})
            session.game.dealer = seed
            session.game.rng = random.Random(seed)
            session.sleep = Mock()
            states = []
            session.broadcast = Mock(side_effect=lambda: states.append(session._build_common()))
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
            # The recap can review completed hands, never the current hidden deal.
            for state in states:
                reviews = state["completed_deals"]
                if state["phase"] not in ("donne_end", "game_end"):
                    self.assertEqual(reviews, [])
                for review in reviews:
                    completed = session.game.donne_logs[review["number"] - 1]
                    self.assertIsNotNone(completed.result)
                    self.assertLessEqual(review["number"], state["donne_number"])
            reviews = session._build_common()["completed_deals"]
            self.assertEqual(len(reviews), accepted)
            for review in reviews:
                completed = session.game.donne_logs[review["number"] - 1]
                self.assertEqual(review["contract"]["suit"], completed.contract.suit.name)
                self.assertEqual(review["hands"], {
                    str(seat): [card_to_dict(card) for card in sorted_hand(hand, completed.contract.suit)]
                    for seat, hand in completed.initial_hands.items()
                })
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
