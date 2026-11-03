"""Un parcours d'export Socket.IO : donnes, confidentialité et reconnexion."""

import copy
import json
import random
import unittest
from unittest.mock import Mock, patch

from belote.bidding import BidAction, BiddingState
from belote.cards import ContractMode, Suit, full_deck
from belote.scoring import compute_donne_score
from belote.trick import TrickState
from game_session import GameSession
from rooms import RoomManager
from serialize import card_id
import server


class GameExportTests(unittest.TestCase):
    def test_export_completed_deals_replay_scores_and_reconnect(self):
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            client = server.socketio.test_client(server.app)
            viewer = server.socketio.test_client(server.app)
            try:
                client.emit("create_room", {"name": "Éloïse"})
                code = next(m["args"][0]["code"] for m in client.get_received()
                            if m["name"] == "room_created")
                room = server.rooms.get(code)
                session = GameSession(room, 5000, bot_ids={seat: "random" for seat in range(4)})
                room.game_session = session
                session.sleep = Mock()
                session.game.rng = random.Random(17)
                session.game.dealer = 0
                session.players[0].name = "Éloïse"
                request = {"code": code, "game_id": session.game_id}

                def export(who=None):
                    return (who or client).emit("export_game", request, callback=True)

                self.assertIn("error", export())  # No completed deal yet.
                live_exports = []
                session.broadcast = lambda: live_exports.append(session.export_completed_game())

                def play(actions, hands=None):
                    for player in session.players.values():
                        player.choose_bid = lambda hand, bidding, legal: actions[len(bidding.history)]
                        player.choose_card = lambda hand, trick, legal: legal[0]
                    if hands:
                        with patch("game_session.deal", side_effect=lambda *_: copy.deepcopy(hands)):
                            return session.game.play_one_donne()
                    return session.game.play_one_donne()

                passes = [BidAction.passe()] * 4
                cancelled = play(passes)
                self.assertTrue(cancelled.annulee)
                play([BidAction.enchere(80, Suit.PIQUE), BidAction.coinche(), BidAction.surcoinche()])
                play([BidAction.enchere(80, ContractMode.SANS_ATOUT)] + passes[:3])
                play([BidAction.enchere(80, ContractMode.TOUT_ATOUT)] + passes[:3])
                # A whole hand of trumps: all eight tricks are resolved by the claim.
                hands = {seat: [card for card in full_deck() if card.suit == suit]
                         for seat, suit in enumerate((Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE))}
                play([BidAction.capot(Suit.COEUR)] + passes[:3], hands)

                response = export()
                self.assertTrue(response["filename"].endswith(".json"))
                raw_json = json.dumps(response["game"], ensure_ascii=False)
                data = json.loads(raw_json)
                self.assertIn("Éloïse", raw_json)
                self.assertEqual((data["format"], data["schema_version"]), ("belote_coinchee.game", 1))
                self.assertEqual(data["status"], "in_progress")
                self.assertEqual(data["teams"], {"0": [0, 2], "1": [1, 3]})
                self.assertEqual(len(data["deals"]), 5)
                self.assertTrue(data["deals"][0]["cancelled"])
                self.assertIsNone(data["deals"][0]["result"])
                self.assertEqual(data["deals"][0]["tricks"], [])
                self.assertEqual(data["deals"][1]["contract"]["coinche_state"], "SURCOINCHE")
                self.assertEqual(data["deals"][-1]["claim"]["from_trick"], 1)
                self.assertTrue(all(t["resolved_by_claim"] for t in data["deals"][-1]["tricks"]))
                self.assertEqual(data["deals"][-1]["belote_announcements"], [])

                deck = {card_id(card): card for card in full_deck()}
                for deal in data["deals"]:
                    self.assertEqual(deal["players"]["0"]["bot_id"], "random")
                    remaining = {int(seat): [deck[cid] for cid in cards]
                                 for seat, cards in deal["initial_hands"].items()}
                    self.assertEqual(len({c for hand in remaining.values() for c in hand}), 32)
                    bidding = BiddingState(dealer=deal["dealer"])
                    for entry in deal["bidding_history"]:
                        self.assertEqual(entry["seat"], bidding.current_player)
                        action = next(a for a in bidding.legal_actions()
                                      if a.type.name == entry["type"] and a.points == entry["points"]
                                      and (a.suit.name if a.suit else None) == entry["suit"]
                                      and a.is_capot == entry["is_capot"])
                        bidding.apply(action)
                    if deal["cancelled"]:
                        self.assertTrue(bidding.annulee)
                        continue
                    leader = deal["first_player"]
                    raw_points = {0: 0, 1: 0}
                    for recorded in deal["tricks"]:
                        trick = TrickState(leader=leader, atout=bidding.contract.suit)
                        for entry in recorded["plays"]:
                            seat, card = entry["seat"], deck[entry["card"]]
                            self.assertEqual(trick.current_player, seat)
                            self.assertIn(card, trick.legal_cards_for(remaining[seat]))
                            trick.play(seat, card)
                            remaining[seat].remove(card)
                        self.assertEqual(trick.winner(), recorded["winner"])
                        self.assertEqual(trick.points(), recorded["points"])
                        leader = trick.winner()
                        raw_points[leader % 2] += trick.points()
                    self.assertTrue(all(not hand for hand in remaining.values()))
                    result = deal["result"]
                    recomputed = compute_donne_score(
                        bidding.contract, raw_points,
                        leader, result["capot_team"], result["belote_team"],
                        {int(t): p for t, p in result["belote_points"].items()})
                    self.assertEqual({str(t): p for t, p in recomputed.final_scores.items()}, result["final_scores"])
                self.assertEqual(data["cumulative_scores"],
                                 {str(t): p for t, p in session.game.cumulative_scores.items()})
                # Each live snapshot contains only immutable, complete earlier deals.
                for snapshot in live_exports:
                    for deal in snapshot["deals"]:
                        self.assertTrue(deal["cancelled"] or len(deal["tricks"]) == 8)
                session.ctx.phase = "bidding"
                session.ctx.hands = hands
                self.assertEqual(export()["game"]["deals"], response["game"]["deals"])
                self.assertNotIn("hands", export()["game"])
                self.assertIn("error", export(viewer))  # Guessing a code does not grant access.
                viewer.emit("join_lobby", {"code": code, "name": "Spectateur"})
                self.assertEqual(export(viewer)["game"]["deals"], response["game"]["deals"])
                # New identity on the next deal does not rewrite the past.
                session.players[0].name = "Nouveau joueur"
                session.game.target_score = 100
                play([BidAction.enchere(80, Suit.COEUR)] + passes[:3], hands)
                final = export()["game"]
                self.assertEqual(final["status"], "finished")
                self.assertIsNotNone(final["winner_team"])
                self.assertEqual(final["deals"][0]["players"]["0"]["name"], "Éloïse")
                self.assertEqual(final["deals"][-1]["players"]["0"]["name"], "Nouveau joueur")
                client.disconnect()
                client = server.socketio.test_client(server.app)
                client.emit("join_lobby", {"code": code, "name": "Éloïse"})
                self.assertEqual(export()["game"]["deals"], final["deals"])
                request["game_id"] = "ancienne-partie"
                self.assertIn("error", export())
                room.game_session = None
                self.assertIn("error", export())
            finally:
                client.disconnect()
                viewer.disconnect()


if __name__ == "__main__":
    unittest.main()
