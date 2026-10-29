"""Representative SA/TA journeys, from the repository PDF (§11)."""

import unittest
import copy
import random
from unittest.mock import Mock, patch

from belote.bidding import ActionType, BidAction, BiddingState, Contract, CoincheState
from belote.bots import BOT_REGISTRY, create_bot
from belote.cards import Card, ContractMode, Rank, Suit, full_deck
from belote.claim import find_claim, play_claim
from belote.trick import TrickState, legal_cards, trick_winner
from belote.game import Donne
from belote.scoring import find_belotes, belote_points_by_team, compute_donne_score
from game_session import GameSession
from rooms import Room
from serialize import sorted_hand


SA, TA = ContractMode.SANS_ATOUT, ContractMode.TOUT_ATOUT


def cards(*codes):
    return [Card(Rank(rank), Suit[suit]) for rank, suit in (code.split('_') for code in codes)]


class ContractModeTests(unittest.TestCase):
    def test_bidding_and_play_without_cutting(self):
        self.assertEqual(len(full_deck()), 32)  # SA/TA must never become card suits.
        for mode, values, winner in ((SA, (19, 10, 4, 3, 2, 0, 0, 0), 0),
                                     (TA, (13, 9, 6, 5, 3, 2, 0, 0), 1)):
            with self.subTest(mode=mode):
                state = BiddingState(dealer=1)
                state.apply(BidAction.enchere(80, mode))
                for _ in range(3):
                    state.apply(BidAction.passe())
                self.assertTrue(state.finished)
                self.assertEqual(state.contract.suit, mode)
                ordered = sorted_hand(cards('A_COEUR', '10_COEUR', 'R_COEUR', 'D_COEUR',
                                            'V_COEUR', '9_COEUR', '8_COEUR', '7_COEUR'), mode)
                self.assertEqual(tuple(c.points(mode) for c in ordered), values)
                self.assertEqual(sum(c.points(mode) for c in full_deck()), 152)
                plays = list(enumerate(cards('A_COEUR', 'V_COEUR', '9_COEUR', 'V_PIQUE')))
                self.assertEqual(trick_winner(plays, mode), winner)  # Off-suit J never cuts.
                hand = cards('V_COEUR', '7_COEUR', 'V_PIQUE')
                legal = legal_cards(hand, [(3, cards('A_COEUR')[0])], mode, 0)
                self.assertEqual(legal, hand[:1] if mode is TA else hand[:2])
                # Partner holds the trick: TA still requires climbing, SA does not.
                legal = legal_cards(hand, [(2, cards('A_COEUR')[0]), (3, cards('7_TREFLE')[0])], mode, 0)
                self.assertEqual(legal, hand[:1] if mode is TA else hand[:2])
                self.assertEqual(legal_cards(hand, [(3, cards('A_CARREAU')[0])], mode, 0), hand)
                masters = {0: ordered[:2], 1: cards('8_PIQUE', '7_PIQUE'),
                           2: ordered[2:4], 3: cards('8_TREFLE', '7_TREFLE')}
                claim = find_claim(masters, 0, mode)
                self.assertIsNotNone(claim)
                self.assertEqual([t.winner() for t in play_claim(masters, 0, mode, claim)], [0, 0])
        # Aces spread across suits -> SA; jacks and a belote -> TA, not a cut hunt.
        openings = {
            SA: cards('V_PIQUE', 'A_PIQUE', 'A_COEUR', '10_COEUR', 'A_TREFLE', '10_TREFLE', 'A_CARREAU', '10_CARREAU'),
            TA: cards('V_PIQUE', 'V_COEUR', 'V_TREFLE', 'R_CARREAU', 'D_CARREAU', '7_CARREAU', '8_TREFLE', '7_COEUR'),
        }
        for version in range(1, 5):
            for mode, hand in openings.items():
                bot = create_bot('brooklyn_v' + str(version), 0)
                state = BiddingState(dealer=1)
                action = bot.choose_bid(hand, state, state.legal_actions())
                self.assertEqual(action.suit, mode)
                self.assertEqual(bot.choose_bid(hand, state, state.legal_actions()), action)
                if mode is SA:
                    hand = cards('A_PIQUE', '10_PIQUE', 'A_COEUR', '7_COEUR', '7_TREFLE', '8_TREFLE', '7_CARREAU', '8_CARREAU')
                bot.notify_donne_start()
                state = BiddingState(dealer=1)
                mode_legal = [a for a in state.legal_actions() if a.type is not ActionType.ENCHERE or a.suit is mode]
                action = bot.choose_bid(hand, state, mode_legal)
                state.apply(action)
                # Opponents pass; partner supports with two OTHER colour masters.
                state.apply(BidAction.passe())
                support = (cards('A_TREFLE', 'A_CARREAU', 'R_PIQUE', 'D_PIQUE', 'R_COEUR', 'D_COEUR', '9_TREFLE', '9_CARREAU')
                           if mode is SA else
                           cards('V_CARREAU', '9_CARREAU', '7_TREFLE', '8_COEUR', '7_PIQUE', '8_PIQUE', '10_PIQUE', '10_TREFLE'))
                self.assertFalse(set(hand) & set(support))
                partner = create_bot('brooklyn_v' + str(version), 2)
                legal = [a for a in state.legal_actions() if a.type is not ActionType.ENCHERE or a.suit is mode]
                raised = partner.choose_bid(support, state, legal)
                self.assertEqual(raised, BidAction.enchere(action.points + 20, mode))
                self.assertEqual(partner.choose_bid(support, state, legal), raised)
                state.apply(raised)
                state.apply(BidAction.passe())
                # Opener already described its hand: it cannot spend belote twice.
                only_mode = lambda: [a for a in state.legal_actions() if a.type is not ActionType.ENCHERE or a.suit is mode]
                self.assertEqual(bot.choose_bid(hand, state, only_mode()), BidAction.passe())
                state.apply(BidAction.passe())
                state.apply(BidAction.enchere(raised.points + 10, mode))
                self.assertEqual(partner.choose_bid(support, state, only_mode()), BidAction.passe())
                bot.notify_donne_start()
                fresh = BiddingState(dealer=1)
                fresh_legal = [a for a in fresh.legal_actions() if a.type is not ActionType.ENCHERE or a.suit is mode]
                self.assertEqual(bot.choose_bid(hand, fresh, fresh_legal), action)
                # An eight-card master sequence guarantees a mode capot.
                certain = [Card(rank, Suit.PIQUE) for rank in Rank]
                fresh = BiddingState(dealer=1)
                only_mode = [a for a in fresh.legal_actions() if a.type is not ActionType.ENCHERE or a.suit is mode]
                self.assertEqual(bot.choose_bid(certain, fresh, only_mode), BidAction.capot(mode))

        # Follow a purge across losses and re-entries; short masters stay in hand.
        for version in range(1, 5):
            for mode, top, middle, missing, first_followers in (
                (SA, 'A', 'R', '10', ('8', 'D', 'V')),
                (TA, 'V', 'A', '9', ('8', 'D', '10')),
            ):
                def ready(hand):
                    bot = create_bot('brooklyn_v' + str(version), 0)
                    auction = BiddingState(dealer=1)
                    bot.choose_bid(hand, auction, auction.legal_actions())
                    bot.notify_contract(Contract(0, 0, 80, mode, False))
                    return bot
                def lead(bot, hand):
                    trick = TrickState(0, mode)
                    return bot.choose_card(hand, trick, trick.legal_cards_for(hand))
                def complete(bot, plays, winner):
                    self.assertEqual(trick_winner(plays, mode), winner)
                    self.assertEqual(len({card for _, card in plays}), 4)
                    for _, card in plays:
                        self.assertNotIn(card.rank, bot.played_by_suit[card.suit])
                    bot.notify_trick_result(plays, winner)
                hand = cards(top+'_PIQUE', middle+'_PIQUE', 'R_PIQUE' if mode is TA else '9_PIQUE',
                             '7_PIQUE', top+'_COEUR', '10_TREFLE', 'R_TREFLE', '7_CARREAU')
                bot = ready(hand)
                first = cards(top+'_PIQUE')[0]
                self.assertEqual(lead(bot, hand), first)
                hand.remove(first)
                complete(bot, [(0, first)] + [(p, cards(r+'_PIQUE')[0])
                                              for p, r in enumerate(first_followers, 1)], 0)
                # The 10 (SA) / 9 (TA) is unseen: force it with the 7, retaining
                # the next honour and the short-suit master.
                low = cards('7_PIQUE')[0]
                self.assertEqual(lead(bot, hand), low)
                hand.remove(low)
                complete(bot, [(0, low), (1, cards(missing+'_PIQUE')[0]),
                               (2, cards('8_CARREAU')[0]), (3, cards('7_COEUR')[0])], 1)
                # After a side-suit re-entry, the next spade is now master.
                side = cards('R_TREFLE')[0]
                hand.remove(side)
                complete(bot, [(1, cards('7_TREFLE')[0]), (2, cards('8_TREFLE')[0]),
                               (3, cards('D_TREFLE')[0]), (0, side)], 0)
                self.assertEqual(lead(bot, hand), cards(middle+'_PIQUE')[0])
                # A three-card suit needs its top TWO; a short lone master
                # must not be cashed just because it is currently unbeatable.
                short = cards(top+'_COEUR', '8_COEUR', '7_COEUR', '10_CARREAU',
                              '8_CARREAU', '7_CARREAU', '8_TREFLE', '7_TREFLE')
                bot = ready(short)
                self.assertNotEqual(lead(bot, short), cards(top+'_COEUR')[0])
                second = '10' if mode is SA else '9'
                long = cards(top+'_COEUR', second+'_COEUR', '7_COEUR', '10_CARREAU',
                             '8_CARREAU', '7_CARREAU', '8_TREFLE', '7_TREFLE')
                bot = ready(long)
                first = lead(bot, long)
                self.assertEqual(first, cards(top+'_COEUR')[0])
                long.remove(first)
                complete(bot, [(0, first), (1, cards('R_COEUR')[0]),
                               (2, cards('D_COEUR')[0]), (3, cards('V_COEUR' if mode is SA else 'A_COEUR')[0])], 0)
                self.assertEqual(lead(bot, long), cards(second+'_COEUR')[0])
                self.assertIn(Suit.COEUR, bot.mode_purge_suits)
                bot.notify_donne_start()
                self.assertEqual(bot.mode_purge_suits, set())
                auction = BiddingState(dealer=1)
                bot.choose_bid(short, auction, auction.legal_actions())
                bot.notify_contract(Contract(0, 0, 80, mode, False))
                self.assertEqual(bot.mode_purge_suits, set())
                for both_void in (False, True):
                    # Both enemy discards prove only partner can hold the
                    # missing master. One enemy void alone is insufficient.
                    spent = '9' if mode is SA else '8'
                    hand = cards(top+'_COEUR', '8_COEUR', '7_COEUR', 'R_PIQUE',
                                 '7_PIQUE', spent+'_PIQUE', top+'_TREFLE', '7_CARREAU')
                    bot = ready(hand)
                    own = cards(spent+'_PIQUE')[0]
                    hand.remove(own)
                    complete(bot, [(2, cards(missing+'_PIQUE')[0]), (3, cards('8_CARREAU')[0]),
                                   (0, own), (1, cards('8_TREFLE' if both_void else ('8_PIQUE' if mode is SA else '10_PIQUE'))[0])], 2)
                    own = cards(top+'_COEUR')[0]
                    hand.remove(own)
                    complete(bot, [(2, cards('9_COEUR')[0]), (3, cards('D_COEUR')[0]),
                                   (0, own), (1, cards('10_COEUR')[0])], 0)
                    self.assertEqual(lead(bot, hand), cards('7_PIQUE' if both_void else '7_COEUR')[0])

    def test_complete_deals_scores_announcements_and_review(self):
        # Each of the four players owns one K/Q pair; other cards are shared.
        hands = {p: [Card(r, s) for r in (Rank.ROI, Rank.DAME)] for p, s in enumerate(Suit)}
        rest = [c for c in full_deck() if c.rank not in (Rank.ROI, Rank.DAME)]
        random.Random(17).shuffle(rest)
        for i, card in enumerate(rest):
            hands[i % 4].append(card)
        for mode in (SA, TA):
            for bot_id in BOT_REGISTRY:
                def players():
                    bots = {p: create_bot(bot_id, p) for p in range(4)}
                    for p, bot in bots.items():
                        bot.rng.seed(p + 32)
                        bot.choose_bid = lambda hand, state, legal: (
                            BidAction.enchere(80, mode) if state.contract is None else BidAction.passe())
                    return bots
                with self.subTest(mode=mode, bot=bot_id):
                    with patch('belote.game.deal', side_effect=lambda *_: copy.deepcopy(hands)):
                        console = Donne(players(), dealer=0).play()
                    session = GameSession(Room('MODES'), target_score=1000)
                    session.game.players = players()
                    session.game.dealer = 0
                    session.sleep = Mock()
                    states = []
                    session.broadcast = lambda: states.append(copy.deepcopy(session._build_common()))
                    with patch('game_session.deal', side_effect=lambda *_: copy.deepcopy(hands)):
                        web = session.game.play_one_donne()
                    self.assertEqual(console.tricks, web.tricks)
                    self.assertEqual(console.result, web.result)
                    self.assertEqual(len(web.tricks), 8)
                    self.assertEqual(sum(web.result.raw_points.values()), 152)
                    expected = {0: 40, 1: 40} if mode is TA else {0: 0, 1: 0}
                    self.assertEqual(web.result.belote_points, expected)
                    self.assertEqual(belote_points_by_team(find_belotes(hands, mode)), expected)
                    for t in (0, 1):
                        dix = 100 if web.result.capot_team is not None else 10
                        self.assertEqual(web.result.total_points[t], web.result.raw_points[t] +
                                         (dix if web.result.dix_de_der_team == t else 0) + expected[t])
                    by_suit = {}
                    for entry in session.ctx.belote_announcements:
                        by_suit.setdefault(entry['suit'], []).append(entry['label'])
                    self.assertTrue(all(labels in (['Belote !'], ['Belote !', 'Rebelote !'])
                                        for labels in by_suit.values()))
                    if mode is SA:
                        self.assertEqual(by_suit, {})
                    else:
                        self.assertTrue(by_suit)
                    for state in states:
                        if state['last_donne_result'] is None:
                            # Only the pairs actually announced may become public.
                            announced = {e['suit'] for e in state['belote_announcements']}
                            visible = belote_points_by_team({s:p for s,p in find_belotes(hands, mode).items()
                                                            if s.name in announced})
                            self.assertEqual(state['belote_points'], {str(t):visible[t] for t in (0, 1)})
                        if state['phase'] not in ('donne_end', 'game_end'):
                            self.assertEqual(state['completed_deals'], [])
                    session.ctx.phase = 'donne_end'
                    review = session._build_common()['completed_deals'][0]
                    self.assertEqual(review['contract']['suit'], mode.name)
                    self.assertEqual(len(review['tricks']), 8)
                    self.assertEqual(review['tricks'][-1]['team_points'],
                                     {str(t): web.result.total_points[t] for t in (0, 1)})
                    for i, trick in enumerate(review['tricks']):
                        self.assertEqual(trick['points'], sum(card.points(mode) for _, card in web.tricks[i]))
                        if i:
                            self.assertTrue(all(trick['team_points'][str(t)] >=
                                                review['tricks'][i-1]['team_points'][str(t)] for t in (0, 1)))
        # Four belotes may all belong to one camp and finance a TA contract.
        all_pairs = {0: [c for c in full_deck() if c.rank in (Rank.ROI, Rank.DAME)]}
        self.assertEqual(belote_points_by_team(find_belotes(all_pairs, TA)), {0:80, 1:0})
        contract = Contract(0, 0, 240, TA, False)
        result = compute_donne_score(contract, {0:152, 1:0}, 0, None, None, {0:80, 1:0})
        self.assertTrue(result.contract_reached)
        self.assertEqual(result.total_points, {0:242, 1:0})
        # All belotes remain imprenables, also when a coinched contract falls.
        contract.coinche_state = CoincheState.COINCHE
        result = compute_donne_score(contract, {0:50, 1:102}, 1, None, None, {0:40, 1:40})
        self.assertFalse(result.contract_reached)
        self.assertEqual(result.score_before_rounding[0], 40)


if __name__ == '__main__':
    unittest.main()
