"""Échiquier de temps du salon : réglage partagé, temps par coup et temps total.

Un humain qui dépasse son temps par coup voit son coup joué par le bot par
défaut ; s'il épuise son temps total, il est dépossédé de son siège et le même
bot finit la partie à sa place.

Lancer depuis la racine : python -B -m unittest discover -s tests -p test_time_control.py
Nécessite les dépendances web de requirements.txt.
"""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from belote.bots import DEFAULT_BOT_ID
from game_session import GameSession, NetworkPlayer
from rooms import MOVE_TIME_PRESETS, PLAYER_SEATS, TOTAL_TIME_PRESETS, Room, RoomManager
import server


class SpyFallback:
    """Bot de secours espionné : il joue normalement, mais on compte ses coups."""

    def __init__(self, inner):
        self.inner = inner
        self.bids = 0
        self.cards = 0

    def choose_bid(self, *args):
        self.bids += 1
        return self.inner.choose_bid(*args)

    def choose_card(self, *args):
        self.cards += 1
        return self.inner.choose_card(*args)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def seated_room(code="TIME") -> Room:
    room = Room(code)
    for seat in PLAYER_SEATS:
        room.take_seat(seat, f"sid-{seat}", f"Joueur {seat + 1}")
    return room


class TimeControlLobbyTests(unittest.TestCase):
    def test_time_control_is_shared_and_locked_once_the_game_starts(self):
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            client = server.socketio.test_client(server.app)
            try:
                client.emit("create_room", {"name": "Zoé"})
                received = client.get_received()
                created = [m["args"][0] for m in received
                           if m["name"] == "room_created"][-1]
                code = created["code"]

                client.emit("set_time_control", {"code": code, "move_time": 30, "total_time": 600})
                lobby = [m["args"][0] for m in client.get_received()
                         if m["name"] == "lobby_update"][-1]
                self.assertEqual(lobby["move_time_limit"], 30)
                self.assertEqual(lobby["total_time_limit"], 600)
                # Le client construit ses sélecteurs à partir des presets du serveur.
                self.assertEqual(lobby["move_time_presets"], list(MOVE_TIME_PRESETS))
                self.assertEqual(lobby["total_time_presets"], list(TOTAL_TIME_PRESETS))

                # Une valeur hors preset ne change rien à l'échiquier en place.
                client.emit("set_time_control", {"code": code, "move_time": 7, "total_time": 600})
                lobby = [m["args"][0] for m in client.get_received()
                         if m["name"] == "lobby_update"][-1]
                self.assertEqual(lobby["move_time_limit"], 30)

                # Partie lancée : les réglages sont verrouillés.
                server.rooms.get(code).game_session = SimpleNamespace(finished=False)
                client.emit("set_time_control", {"code": code, "move_time": 60, "total_time": 0})
                lobby = [m["args"][0] for m in client.get_received()
                         if m["name"] == "lobby_update"][-1]
                self.assertEqual(lobby["move_time_limit"], 30)
            finally:
                client.disconnect()


class TimeControlPlayTests(unittest.TestCase):
    def build_session(self, move_seconds=0.02, total_seconds=30.0):
        """Partie web aux quatre sièges humains, avec des temps comprimés.

        L'échiquier est lu dans la salle au démarrage de la partie, comme en
        production ; le temps par coup est ensuite raccourci pour le test.
        """
        room = seated_room()
        room.move_time_limit = 1
        room.total_time_limit = int(total_seconds)
        session = GameSession(room, target_score=1000, fill_bots=False)
        room.game_session = session
        session.sleep = Mock()
        session.broadcast = Mock()
        session.move_time_limit = move_seconds
        session._clocks = {seat: total_seconds for seat in PLAYER_SEATS}
        # On espionne le bot de secours du siège 0, armé en tête de donne.
        session.arm_fallback_bots()
        session._timeout_bots[0] = SpyFallback(session._timeout_bots[0])
        return room, session

    def play_a_donne(self, session):
        log = session.game.play_one_donne()
        for _ in range(3):
            if not log.annulee:
                break
            log = session.game.play_one_donne()
        self.assertIsNotNone(log.result)
        self.assertEqual(len(log.tricks), 8)
        return log

    def test_move_timeout_is_played_by_the_default_bot(self):
        room, session = self.build_session(move_seconds=0.02, total_seconds=30.0)
        # L'état commun porte l'échiquier et les horloges, pour l'affichage.
        common = session._build_common()
        self.assertEqual(common["time_control"]["total_seconds"], 30)
        self.assertGreater(common["time_control"]["move_seconds"], 0)
        self.assertEqual(set(common["clocks"]), {"0", "1", "2", "3"})
        self.assertIsNone(common["turn_deadline"])

        self.play_a_donne(session)

        spy = session._timeout_bots[0]
        self.assertGreaterEqual(spy.bids, 1)     # enchères jouées par le bot de secours
        self.assertGreaterEqual(spy.cards, 1)    # cartes jouées par le bot de secours
        # Le joueur garde sa place et son temps total, amputé de sa réflexion.
        self.assertIsInstance(session.players[0], NetworkPlayer)
        self.assertTrue(room.seats[0].occupied)
        self.assertLess(session._clocks[0], 30.0)
        self.assertGreater(session._clocks[0], 0.0)

    def test_total_timeout_replaces_the_human_by_the_default_bot(self):
        room, session = self.build_session(move_seconds=0.02, total_seconds=30.0)
        session._clocks[0] = 0.01              # siège 0 n'a plus que le temps d'un souffle

        with patch("game_session.socketio") as fake_sio:
            self.play_a_donne(session)

        # Le joueur est viré : le bot par défaut a pris son siège pour la donne.
        self.assertNotIsInstance(session.players[0], NetworkPlayer)
        self.assertEqual(session.bot_profiles[0]["id"], DEFAULT_BOT_ID)
        self.assertFalse(room.seats[0].occupied)
        self.assertEqual(room.bot_choices[0], DEFAULT_BOT_ID)
        self.assertEqual(session._clocks[0], 0.0)
        # Sa connection reste connectée, mais en spectateur.
        self.assertNotIn("sid-0", [slot.sid for slot in room.seats.values()])
        self.assertIn("sid-0", room.spectators)
        # Le coup est joué, et tout le monde est prévenu.
        sent_to_room = [call.args[1]["message"] for call in fake_sio.emit.call_args_list
                        if call.args[0] == "error_message" and call.kwargs.get("room") == room.code]
        self.assertTrue(any("épuisé son temps" in message for message in sent_to_room))
        kicked = [call for call in fake_sio.emit.call_args_list if call.args[0] == "seat_lost"]
        self.assertEqual(len(kicked), 1)
        self.assertEqual(kicked[0].kwargs.get("to"), "sid-0")


if __name__ == "__main__":
    unittest.main()
