"""Salon public : annuaire, spectateurs pendant la partie et reprise d'un siège de bot.

Parcours nominal d'une seule trajectoire : un salon public figure dans
l'annuaire, un visiteur le rejoint pendant la partie sans recevoir de main,
puis monte à table en reprenant un siège de bot à la donne suivante. Le
salon privé sert de témoin : ni annuaire, ni spectateur, ni reprise.
"""

import unittest
from unittest.mock import patch

from game_session import NetworkPlayer
from rooms import RoomManager
import server


class SpectatorTests(unittest.TestCase):
    def test_public_directory_spectators_and_bot_takeover(self):
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            clients = []

            def connect(name, code=None, visibility="public"):
                client = server.socketio.test_client(server.app)
                clients.append(client)
                if code:
                    client.emit("join_lobby", {"code": code, "name": name})
                else:
                    client.emit("create_room", {"name": name, "visibility": visibility})
                return client

            def latest(client, event):
                return [m["args"][0] for m in client.get_received() if m["name"] == event][-1]

            def last_state(client):
                return [m["args"][0] for m in client.get_received()
                        if m["name"] == "state_update"][-1]

            try:
                host = connect("Hôte", visibility="public")
                created = latest(host, "room_created")
                public_code, public_visibility = created["code"], created["visibility"]
                self.assertEqual(public_visibility, "public")

                # Un salon privé ne rejoint pas l'annuaire.
                private = connect("Solitaire", visibility="private")
                private_code = latest(private, "room_created")["code"]
                self.assertEqual(server.rooms.get(private_code).visibility, "private")

                # Deux joueurs assis et deux bots : l'annuaire montre le remplissage.
                bob = connect("Bob", public_code)
                host.emit("take_seat", {"code": public_code, "seat": 0})
                bob.emit("take_seat", {"code": public_code, "seat": 1})

                host.emit("list_public_rooms", {})
                listing = latest(host, "public_rooms")["rooms"]
                listed = {room["code"]: room for room in listing}
                self.assertIn(public_code, listed)
                self.assertNotIn(private_code, listed)
                self.assertEqual(listed[public_code]["phase"], "lobby")
                self.assertEqual(listed[public_code]["player_count"], 2)

                room = server.rooms.get(public_code)
                session = server.GameSession(room, target_score=1000)
                room.game_session = session

                # Le visiteur entre : spectateur, sans siège et sans main.
                eve = connect("Ève", public_code)
                joined = latest(eve, "lobby_joined")
                self.assertIsNone(joined["your_seat"])
                self.assertEqual(joined["spectator_count"], 1)
                session.ctx.phase = "donne_end"
                session.broadcast()
                state = last_state(eve)
                self.assertEqual(state["your_seat"], "spectator")
                self.assertEqual(state["your_hand"], [])
                self.assertFalse(state["your_turn"])
                self.assertEqual(state["legal_card_ids"], [])

                # Entre deux donnes, la reprise d'un siège de bot est acceptée.
                self.assertTrue(session.accepts_takeovers())
                eve_sid = next(sid for sid, info in server.sid_info.items()
                               if info["name"] == "Ève")
                eve.emit("request_takeover", {"code": public_code, "seat": 2})
                self.assertEqual(room.pending_takeovers[2], (eve_sid, "Ève"))
                # Le bot continue de jouer la donne en cours : siège toujours libre.
                self.assertFalse(room.seats[2].occupied)
                session.broadcast()
                announcing = last_state(eve)
                self.assertEqual(announcing["your_seat"], "spectator")
                self.assertEqual(announcing["pending_takeovers"], {"2": "Ève"})

                # Le siège promis est refusé à un autre visiteur.
                frank = connect("Frank", public_code)
                self.assertIsNone(latest(frank, "lobby_joined")["your_seat"])
                frank.emit("request_takeover", {"code": public_code, "seat": 2})
                self.assertEqual(room.pending_takeovers[2], (eve_sid, "Ève"))

                # Au début de la donne suivante, Ève remplace le bot avant la distribution.
                session.ctx.phase = "bidding"
                session.apply_pending_takeovers()
                self.assertEqual(room.seats[2].name, "Ève")
                self.assertTrue(room.seats[2].occupied)
                self.assertIsInstance(session.players[2], NetworkPlayer)
                self.assertNotIn(2, session.bot_profiles)
                self.assertEqual(room.spectator_count(), 1)  # Frank est toujours là
                session.broadcast()
                self.assertEqual(last_state(eve)["your_seat"], 2)
                self.assertEqual(last_state(frank)["your_seat"], "spectator")

                # Pendant une donne, aucune reprise n'est acceptée.
                frank.emit("request_takeover", {"code": public_code, "seat": 3})
                self.assertNotIn(3, room.pending_takeovers)

                # Un salon privé ne connaît ni spectateur ni reprise.
                self.assertEqual(server.rooms.get(private_code).spectator_count(), 0)
                solitaire_sid = next(sid for sid, info in server.sid_info.items()
                                     if info["name"] == "Solitaire")
                self.assertFalse(server.rooms.get(private_code)
                                 .request_takeover(0, solitaire_sid, "Solitaire"))
            finally:
                for client in clients:
                    if client.is_connected():
                        client.disconnect()


if __name__ == "__main__":
    unittest.main()
